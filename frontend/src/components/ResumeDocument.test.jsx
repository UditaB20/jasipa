import { describe, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ResumeDocument, { toBlocks } from "./ResumeDocument";
import { tc } from "../test/tc";

describe("ResumeDocument", () => {
  tc("Resume display – PDF line wraps", "a sentence broken across lines and bullet lines", "wrapped lines joined into one paragraph; bullets grouped in a list", () => {
    expect(toBlocks(["Built payment APIs used", "by 40 teams.", "• Python", "• SQL"])).toEqual([
      { type: "p", text: "Built payment APIs used by 40 teams." }, { type: "list", items: ["Python", "SQL"] }]);
  });
  tc("Resume display – section headings", "sections Summary, Experience, Skills", "each title rendered as a heading with its own content", () => {
    render(<ResumeDocument sections={[
      { title: null, lines: ["Jordan Rivera"] },
      { title: "Summary", lines: ["Backend engineer."] },
      { title: "Experience", lines: ["Senior Engineer, Northwind"] },
      { title: "Skills", lines: ["• Python", "• SQL"] }]} />);
    expect(screen.getAllByRole("heading").map((h) => h.textContent)).toEqual(["Summary", "Experience", "Skills"]);
    expect(screen.getByText("Jordan Rivera")).toHaveClass("lead");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
  });
});
