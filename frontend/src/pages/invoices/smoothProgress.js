// Backend chi bao tien do theo moc (5 / 15 / 55 / 95%). Giua 2 moc co the mat vai chuc giay (doc chu, cho Gemini)
// nen thanh bi dung. Ham nay cho thanh "nhich" dan ve phia moc ke tiep (khong bao gio toi het moc do),
// va nhay thang len khi backend bao moc moi. Goi moi lan hoi tien do (1 giay).
const MARKS = [0, 15, 55, 95, 100];

export function creep(shown, real) {
  const base = Math.max(shown || 0, real);
  const next = MARKS.find((m) => m > real) ?? 100;
  const ceil = next - 1;                          // cho dung truoc moc ke tiep
  if (base >= ceil) return Math.min(base, 99);
  return Math.min(base + Math.max(0.25, (ceil - base) * 0.05), ceil);
}
