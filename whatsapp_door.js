const { default: makeWASocket, useMultiFileAuthState } = require("@whiskeysockets/baileys")
const pino = require("pino")
const readline = require("readline")

function out(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n")
}

async function start() {
  const { state, saveCreds } = await useMultiFileAuthState("./wa_auth")
  const sock = makeWASocket({
    auth: state,
    printQRInTerminal: false,
    logger: pino({ level: "silent" }),
    browser: ["Xephon", "Chrome", "1.0.0"],
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
  const rl = readline.createInterface({ input: process.stdin })
  rl.on("line", async (line) => {
    try {
      const data = JSON.parse(line)
      if (data.type === "send" && data.chat && data.text) {
        await sock.sendMessage(data.chat, { text: String(data.text).slice(0, 4000) })
      }
      if (data.type === "pair" && data.phone) {
        const code = await sock.requestPairingCode(String(data.phone).replace(/\D/g, ""))
        out({ type: "code", code, id: data.id || "" })
      }
    } catch (e) {
      out({ type: "error", error: String(e), id: "" })
    }
  })
  sock.ev.on("connection.update", (update) => {
    if (update.connection === "open") out({ type: "ready" })
    if (update.connection === "close") out({ type: "closed" })
  })
}

start().catch((e) => {
  out({ type: "error", error: String(e) })
  process.exit(1)
})
