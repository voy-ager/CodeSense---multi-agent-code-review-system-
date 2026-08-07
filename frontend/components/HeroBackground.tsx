"use client";

const LINES: {
  text: string;
  isAdd: boolean;
  left: number;
  duration: number;
  delay: number;
  size: number;
}[] = [
  { text: '+ const stmt = db.prepare("SELECT * FROM users WHERE id = ?")', isAdd: true,  left: 2,  duration: 20, delay: 0,   size: 8.5 },
  { text: '- const q = "SELECT * FROM users WHERE id=" + userId',          isAdd: false, left: 20, duration: 24, delay: -5,  size: 8   },
  { text: '+ if (!req.headers.authorization) return res.status(401)',       isAdd: true,  left: 36, duration: 19, delay: -10, size: 8.5 },
  { text: '- // TODO: add authentication check',                            isAdd: false, left: 54, duration: 22, delay: -3,  size: 8   },
  { text: '+ const hash = await bcrypt.hash(password, 12)',                isAdd: true,  left: 66, duration: 26, delay: -15, size: 8.5 },
  { text: '- const hash = md5(password)',                                  isAdd: false, left: 6,  duration: 21, delay: -8,  size: 8   },
  { text: '+ const users = await User.findAll({ where: { active: true } })', isAdd: true, left: 42, duration: 28, delay: -19, size: 8 },
  { text: '- for (const id of ids) { const u = await User.findById(id) }', isAdd: false, left: 74, duration: 23, delay: -12, size: 7.5 },
  { text: '+ expect(result).toBeDefined()',                                isAdd: true,  left: 26, duration: 18, delay: -4,  size: 8.5 },
  { text: '- // test pending',                                             isAdd: false, left: 60, duration: 27, delay: -17, size: 8   },
  { text: '+ const apiKey = process.env.OPENAI_API_KEY',                  isAdd: true,  left: 13, duration: 30, delay: -23, size: 8   },
  { text: '- const API_KEY = "sk-prod-abc123xyz789efg"',                  isAdd: false, left: 82, duration: 22, delay: -7,  size: 8   },
];

export default function HeroBackground() {
  return (
    <div
      aria-hidden="true"
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        overflow: "hidden",
        zIndex: 0,
      }}
    >
      {LINES.map((line, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            bottom: -20,
            left: `${line.left}%`,
            fontFamily: "ui-monospace, 'Cascadia Code', 'Source Code Pro', monospace",
            fontSize: `${line.size}px`,
            color: line.isAdd
                ? "rgba(52, 211, 153, 0.18)"
                : "rgba(248, 113, 113, 0.16)",
            whiteSpace: "nowrap",
            animation: `diffFloat ${line.duration}s linear ${line.delay}s infinite`,
            letterSpacing: "-0.02em",
            lineHeight: 1,
          }}
        >
          {line.text}
        </div>
      ))}
    </div>
  );
}