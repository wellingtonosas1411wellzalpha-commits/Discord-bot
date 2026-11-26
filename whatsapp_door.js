const { default: makeWASocket, useMultiFileAuthState, Browsers, DisconnectReason } = require("@whiskeysockets/baileys")
const pino = require("pino")
const readline = require("readline")
const fs = require("fs")

function out(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n")
}

let sock = null
let pairing = false
const sentIds = new Set()
const sentByChat = new Map()
const recent = new Map()
const recentByChat = new Map()

function rememberSent(sent) {
  const id = sent?.key?.id
  const chat = sent?.key?.remoteJid
  if (!id) return
  sentIds.add(id)
  if (sentIds.size > 800) sentIds.delete(sentIds.values().next().value)
  if (!chat) return
  const list = sentByChat.get(chat) || []
  list.push(sent.key)
  sentByChat.set(chat, list.slice(-30))
}

function rememberIncoming(msg, text) {
  const id = msg?.key?.id
  if (!id) return
  recent.set(id, {
    text,
    name: msg.pushName || "Someone",
    from: (msg.key.participant || msg.key.remoteJid || "").split("@")[0],
    chat: msg.key.remoteJid,
    key: msg.key,
  })
  const chat = msg.key.remoteJid
  if (chat) {
    const list = recentByChat.get(chat) || []
    list.push(msg.key)
    recentByChat.set(chat, list.slice(-40))
  }
  if (recent.size > 800) recent.delete(recent.keys().next().value)
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function openSocket() {
  fs.mkdirSync("./wa_auth", { recursive: true })
  const { state, saveCreds } = await useMultiFileAuthState("./wa_auth")
  sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
    logger: pino({ level: "silent" }),
    browser: Browsers.ubuntu("Chrome"),
    markOnlineOnConnect: false,
    syncFullHistory: false,
    connectTimeoutMs: 20000,
  })
  sock.ev.on("creds.update", saveCreds)
  sock.ev.on("messages.upsert", async ({ messages }) => {
    for (const msg of messages) {
      if (!msg.message || msg.key.fromMe) continue
      const content = msg.message.ephemeralMessage?.message || msg.message.viewOnceMessage?.message || msg.message
      const text = content.conversation
        || content.extendedTextMessage?.text
        || content.imageMessage?.caption
        || content.videoMessage?.caption
        || content.documentMessage?.caption
        || ""
      const linkUrl = content.extendedTextMessage?.canonicalUrl
        || content.extendedTextMessage?.matchedText
        || content.extendedTextMessage?.text
        || ""
      const quoted = content.extendedTextMessage?.contextInfo
        || content.imageMessage?.contextInfo
        || content.videoMessage?.contextInfo
        || {}
      rememberIncoming(msg, text || linkUrl)
      const idOf = (jid) => String(jid || "").split("@")[0].split(":")[0]
      const participant = msg.key.participant || ""
      const participantAlt = msg.key.participantAlt || msg.key.participantPn || ""
      async function phoneFor(jid) {
        if (!jid) return ""
        if (String(jid).endsWith("@s.whatsapp.net")) return idOf(jid)
        try {
          if (String(msg.key.remoteJid || "").endsWith("@g.us")) {
            const meta = await sock.groupMetadata(msg.key.remoteJid)
            const found = (meta.participants || []).find(p => p.id === jid || idOf(p.id) === idOf(jid))
            if (found?.phoneNumber) return idOf(found.phoneNumber)
          }
        } catch (e) {}
        try {
          const mapped = await sock.signalRepository?.lidMapping?.getPNForLID?.(jid)
          return idOf(mapped)
        } catch (e) {}
        return ""
      }
      let phone = idOf(participantAlt || msg.key.remoteJidAlt || "") || await phoneFor(participant)
      const rawMentions = quoted.mentionedJid || content.extendedTextMessage?.contextInfo?.mentionedJid || []
      const mentions = []
      for (const jid of rawMentions) {
        const id = idOf(jid)
        const mentionPhone = String(jid).endsWith("@s.whatsapp.net") ? id : await phoneFor(jid)
        mentions.push({ id, phone: mentionPhone, jid, name: "" })
      }
      out({
        type: "message",
        from: idOf(participant || msg.key.remoteJid),
        phone,
        lid: String(participant).endsWith("@lid") ? idOf(participant) : "",
        chat: msg.key.remoteJid,
        name: msg.pushName || "You",
        text: [text, linkUrl].filter(Boolean).join("\n"),
        quoted: quoted.stanzaId || "",
        quotedParticipant: quoted.participant || "",
        participant: participant || msg.key.remoteJid || "",
        isGroup: String(msg.key.remoteJid || "").endsWith("@g.us"),
        replyToBot: Boolean(quoted.stanzaId && sentIds.has(quoted.stanzaId)),
        mentions,
        msgId: msg.key.id || "",
      })
    }
  })
  sock.ev.on("messages.delete", async (item) => {
    const keys = item.keys || item || []
    for (const key of keys) {
      const saved = recent.get(key.id)
      if (!saved) continue
      out({ type: "deleted", chat: key.remoteJid, from: saved.from, name: saved.name, text: saved.text })
    }
  })
  sock.ev.on("connection.update", async (update) => {
    if (update.connection === "open") out({ type: "ready" })
    if (update.connection === "close" && !pairing) {
      const code = update.lastDisconnect?.error?.output?.statusCode
      out({ type: "closed", code })
      if (code !== DisconnectReason.loggedOut) {
        await sleep(3000)
        try { await openSocket() } catch (e) { out({ type: "error", error: String(e) }) }
      }
    }
  })
  return sock
}

async function freshPairSocket() {
  pairing = true
  try { sock?.end?.() } catch (e) {}
  await sleep(500)
  fs.rmSync("./wa_auth", { recursive: true, force: true })
  fs.mkdirSync("./wa_auth", { recursive: true })
  return await openSocket()
}

async function makeCode(phone) {
  const current = await freshPairSocket()
  await sleep(800)
  const raw = await current.requestPairingCode(phone)
  return String(raw).replace(/[^A-Za-z0-9]/g, "").toUpperCase()
}

async function start() {
  await openSocket()
  const rl = readline.createInterface({ input: process.stdin })
  rl.on("line", async (line) => {
    let data = {}
    try {
      data = JSON.parse(line)
      if (data.type === "send" && data.chat && data.text && sock) {
        const sent = await sock.sendMessage(data.chat, { text: String(data.text).slice(0, 4000), mentions: data.mentions || [] })
        rememberSent(sent)
      }
      if (data.type === "delete" && data.chat && data.msgId && sock) {
        await sock.sendMessage(data.chat, { delete: { remoteJid: data.chat, fromMe: false, id: data.msgId, participant: data.participant || undefined } })
      }
      if (data.type === "react" && data.chat && data.msgId && sock) {
        await sock.sendMessage(data.chat, { react: { text: data.emoji || "👍", key: { remoteJid: data.chat, id: data.msgId, participant: data.participant || undefined } } })
      }
      if (data.type === "poll" && data.chat && sock) {
        await sock.sendMessage(data.chat, { poll: { name: data.question || "Poll", values: data.options || [], selectableCount: 1 } })
      }
      if (data.type === "image" && data.chat && sock) {
        const buf = fs.readFileSync(data.file)
        const sent = await sock.sendMessage(data.chat, { image: buf, caption: data.text || "" })
        rememberSent(sent)
      }
      if (data.type === "purge" && data.chat && sock) {
        const list = (recentByChat.get(data.chat) || []).slice(-(data.count || 10))
        for (const key of list) {
          try { await sock.sendMessage(data.chat, { delete: key }) } catch (e) {}
        }
      }
      if (data.type === "clear" && data.chat && sock) {
        const list = (sentByChat.get(data.chat) || []).slice(-(data.count || 10))
        for (const key of list) {
          try { await sock.sendMessage(data.chat, { delete: key }) } catch (e) {}
        }
      }
      if (data.type === "save_auth" && data.files && sock) {
        // auth files are written by Python before restart
      }
      if ((data.type === "group_remove" || data.type === "group_add") && data.chat && sock && data.phone) {
        const jid = String(data.phone).replace(/\D/g, "") + "@s.whatsapp.net"
        await sock.groupParticipantsUpdate(data.chat, [jid], data.type === "group_add" ? "add" : "remove")
      }
      if (data.type === "ptag" && data.chat && sock) {
        const meta = await sock.groupMetadata(data.chat)
        const mentions = (meta.participants || []).map(p => p.id)
        const tags = mentions.map(id => "@" + id.split("@")[0]).join(" ")
        await sock.sendMessage(data.chat, { text: (data.text || "") + "\n" + tags, mentions })
      }
      if (data.type === "pair" && data.phone) {
        const phone = String(data.phone).replace(/\D/g, "")
        let clean = ""
        let lastError = null
        for (let attempt = 1; attempt <= 2; attempt++) {
          try {
            clean = await makeCode(phone)
            break
          } catch (e) {
            lastError = e
            await sleep(2000)
          }
        }
        pairing = false
        if (!clean) throw lastError || new Error("Connection Closed")
        const shown = clean.length === 8 ? clean.slice(0, 4) + "-" + clean.slice(4) : clean
        out({ type: "code", code: shown, id: data.id || "" })
      }
    } catch (e) {
      pairing = false
      out({ type: "error", error: String(e.message || e), id: data.id || "" })
    }
  })
}

start().catch((e) => {
  out({ type: "error", error: String(e) })
  process.exit(1)
})
