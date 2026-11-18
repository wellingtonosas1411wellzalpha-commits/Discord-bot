const { default: makeWASocket, useMultiFileAuthState, Browsers } = require("@whiskeysockets/baileys")
const pino = require("pino")
const readline = require("readline")
const fs = require("fs")

function out(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n")
}

let sock = null

async function resetAuth() {
  fs.rmSync("./wa_auth", { recursive: true, force: true })
}

async function openSocket() {
  const { state, saveCreds } = await useMultiFileAuthState("./wa_auth")
  sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
    logger: pino({ level: "silent" }),
    browser: Browsers.ubuntu("Chrome"),
  })
  sock.ev.on("creds.update", saveCreds)
  sock.ev.on("messages.upsert", async ({ messages }) => {
    for (const msg of messages) {
      if (!msg.message || msg.key.fromMe) continue
      const text = msg.message.conversation || msg.message.extendedTextMessage?.text || ""
      if (!text) continue
      out({
        type: "message",
        from: (msg.key.participant || msg.key.remoteJid || "").split("@")[0],
        chat: msg.key.remoteJid,
        name: msg.pushName || "You",
        text,
      })
    }
  })
  sock.ev.on("connection.update", (update) => {
    if (update.connection === "open") out({ type: "ready" })
    if (update.connection === "close") out({ type: "closed" })
  })
  return sock
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
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
      if (data.type === "pair" && data.phone) {
        const phone = String(data.phone).replace(/\D/g, "")
        if (!sock?.authState?.creds?.registered) {
          try { sock?.end?.() } catch (e) {}
          await resetAuth()
          sock = await openSocket()
          await sleep(4000)
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
