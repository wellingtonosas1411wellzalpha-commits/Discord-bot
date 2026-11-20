const { default: makeWASocket, useMultiFileAuthState, Browsers, DisconnectReason } = require("@whiskeysockets/baileys")
const pino = require("pino")
const readline = require("readline")
const fs = require("fs")

function out(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n")
}

let sock = null
let starting = false

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function openSocket() {
  const { state, saveCreds } = await useMultiFileAuthState("./wa_auth")
  sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
    logger: pino({ level: "silent" }),
    browser: Browsers.ubuntu("Chrome"),
    markOnlineOnConnect: false,
    syncFullHistory: false,
  })
  sock.ev.on("creds.update", saveCreds)
  sock.ev.on("messages.upsert", async ({ messages }) => {
    for (const msg of messages) {
      if (!msg.message || msg.key.fromMe) continue
      const text = msg.message.conversation || msg.message.extendedTextMessage?.text || ""
      if (!text) continue
      const quoted = msg.message.extendedTextMessage?.contextInfo || {}
      out({
        type: "message",
        from: (msg.key.participant || msg.key.remoteJid || "").split("@")[0],
        chat: msg.key.remoteJid,
        name: msg.pushName || "You",
        text,
        quoted: quoted.stanzaId || "",
        participant: quoted.participant || msg.key.participant || "",
        isGroup: String(msg.key.remoteJid || "").endsWith("@g.us"),
      })
    }
  })
  sock.ev.on("connection.update", async (update) => {
    if (update.connection === "open") out({ type: "ready" })
    if (update.connection === "close") {
      const code = update.lastDisconnect?.error?.output?.statusCode
      out({ type: "closed", code })
      if (code !== DisconnectReason.loggedOut && !starting) {
        starting = true
        await sleep(2000)
        try { await openSocket() } catch (e) { out({ type: "error", error: String(e) }) }
        starting = false
      }
    }
  })
  return sock
}

async function start() {
  await openSocket()
  const rl = readline.createInterface({ input: process.stdin })
  rl.on("line", async (line) => {
    try {
      const data = JSON.parse(line)
      if (data.type === "send" && data.chat && data.text && sock) {
        await sock.sendMessage(data.chat, { text: String(data.text).slice(0, 4000) })
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
      if (data.type === "ptag" && data.chat && sock) {
        const meta = await sock.groupMetadata(data.chat)
        const mentions = (meta.participants || []).map(p => p.id)
        const tags = mentions.map(id => "@" + id.split("@")[0]).join(" ")
        await sock.sendMessage(data.chat, { text: (data.text || "") + "\n" + tags, mentions })
      }
      if (data.type === "pair" && data.phone) {
        const phone = String(data.phone).replace(/\D/g, "")
        if (!sock?.authState?.creds?.registered) {
          try { sock?.end?.() } catch (e) {}
          fs.rmSync("./wa_auth", { recursive: true, force: true })
          sock = await openSocket()
          await sleep(5000)
        }
        const raw = await sock.requestPairingCode(phone)
        const clean = String(raw).replace(/[^A-Za-z0-9]/g, "").toUpperCase()
        const shown = clean.length === 8 ? clean.slice(0, 4) + "-" + clean.slice(4) : clean
        out({ type: "code", code: shown, id: data.id || "" })
      }
    } catch (e) {
      out({ type: "error", error: String(e), id: "" })
    }
  })
}

start().catch((e) => {
  out({ type: "error", error: String(e) })
  process.exit(1)
})
