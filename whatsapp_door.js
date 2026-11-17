const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require("@whiskeysockets/baileys")
const pino = require("pino")
const readline = require("readline")

const phone = (process.env.WHATSAPP_PHONE || "").replace(/\D/g, "")

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
  if (!state.creds.registered) {
    const code = await sock.requestPairingCode(phone)
    out({ type: "code", code })
  }
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
    } catch (e) {}
  })
  sock.ev.on("connection.update", (update) => {
    if (update.connection === "close") {
      const code = update.lastDisconnect?.error?.output?.statusCode
      if (code !== DisconnectReason.loggedOut) start()
    }
  })
}

start().catch((e) => {
  out({ type: "error", error: String(e) })
  process.exit(1)
})
