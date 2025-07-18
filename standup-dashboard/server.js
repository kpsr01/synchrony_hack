const express = require("express");
const sqlite3 = require("sqlite3").verbose();
const cors = require("cors");
const { GoogleGenerativeAI } = require("@google/generative-ai");
require("dotenv").config();

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });

// Get standup channels
app.get("/api/channels", (req, res) => {
	const db = new sqlite3.Database(
		process.env.DB_PATH || "../slack/standup_messages.db",
	);

	db.all(
		`
    SELECT DISTINCT sc.channel_id, sc.channel_name, sc.team_id,
           COUNT(m.id) as message_count
    FROM standup_channels sc
    LEFT JOIN messages m ON sc.channel_id = m.channel_id 
    AND m.date = ?
    GROUP BY sc.channel_id, sc.channel_name, sc.team_id
  `,
		[req.query.date || new Date().toISOString().split("T")[0]],
		(err, rows) => {
			if (err) {
				res.status(500).json({ error: err.message });
				return;
			}
			res.json(rows);
		},
	);

	db.close();
});

// Get messages for channel and date
app.get("/api/messages/:channelId", (req, res) => {
	const db = new sqlite3.Database(
		process.env.DB_PATH || "../slack/standup_messages.db",
	);
	const { channelId } = req.params;
	const { date } = req.query;

	db.all(
		`
    SELECT user_name, content, timestamp, attachments
    FROM messages 
    WHERE channel_id = ? AND date = ?
    ORDER BY timestamp ASC
  `,
		[channelId, date],
		(err, rows) => {
			if (err) {
				res.status(500).json({ error: err.message });
				return;
			}
			res.json(rows);
		},
	);

	db.close();
});

// Generate AI summary
app.post("/api/summary", async (req, res) => {
	const { messages, date, channelName } = req.body;

	if (!messages || messages.length === 0) {
		return res.json({ summary: "No messages found for this date." });
	}

	const messagesText = messages
		.map(
			(msg) =>
				`**${msg.user_name}:** [${new Date(msg.timestamp).toLocaleTimeString()}] ${msg.content}${msg.attachments > 0 ? ` (${msg.attachments} attachments)` : ""}`,
		)
		.join("\n");

	const prompt = `
    Analyze the following standup messages from ${channelName} on ${date} and provide a brief executive summary in 2-3 sentences.

    Focus ONLY on:
    - Key progress and accomplishments
    - Critical blockers or issues
    - Important decisions made

    Keep it concise and manager-friendly. Avoid formatting like bold text, bullet points, or section headers.

    Messages:
    ${messagesText}
    `;

	try {
		const result = await model.generateContent(prompt);
		const response = await result.response;
		res.json({ summary: response.text() });
	} catch (error) {
		res
			.status(500)
			.json({ error: `Error generating AI summary: ${error.message}` });
	}
});

app.listen(PORT, () => {
	console.log(`Server running on port ${PORT} `);
});
