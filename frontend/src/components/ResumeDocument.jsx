import { resumeSections } from "../lib/format";

const BULLET = /^[•·\-*▪●]\s*/;

/** Groups raw lines into paragraphs and bullet lists. PDF extraction breaks sentences across lines,
 * so a line that does not end a sentence is joined with the next one. */
export function toBlocks(lines) {
  const blocks = [];
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    const last = blocks[blocks.length - 1];
    if (BULLET.test(line)) {
      const item = line.replace(BULLET, "");
      if (last?.type === "list") last.items.push(item);
      else blocks.push({ type: "list", items: [item] });
    } else if (last?.type === "p" && !/[.:;!?)]$/.test(last.text) && /^[a-z(,&]/.test(line)) {
      last.text = `${last.text} ${line}`;
    } else {
      blocks.push({ type: "p", text: line });
    }
  }
  return blocks;
}

export default function ResumeDocument({ sections, text }) {
  const parts = resumeSections(sections, text);
  return (
    <div className="resume-doc">
      {parts.map((section, index) => (
        <section key={index} className="resume-section">
          {section.title ? <h3>{section.title}</h3> : null}
          {toBlocks(section.lines).map((block, i) =>
            block.type === "list" ? (
              <ul key={i}>{block.items.map((item, j) => <li key={j}>{item}</li>)}</ul>
            ) : (
              <p key={i} className={!section.title && index === 0 && i === 0 ? "lead" : undefined}>{block.text}</p>
            ))}
        </section>
      ))}
    </div>
  );
}
