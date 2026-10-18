import colors from "tailwindcss/colors";
import plugin from "tailwindcss/plugin";

// Che do toi cho TOAN BO web (ca trang cua cac thanh vien khac, khong can viet `dark:` o tung cho):
// cac mau co san (slate, red, blue...) duoc doi thanh bien CSS; o che do toi (class `dark` tren <html>)
// moi bien tro sang mau dao nguoc. Che do sang giu nguyen mau mac dinh cua Tailwind.
const FAMILIES = ["slate", "gray", "red", "orange", "amber", "yellow", "green", "emerald", "sky", "blue", "indigo", "violet", "rose"];
const SHADES = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];
const NEUTRAL = new Set(["slate", "gray"]);

// ban do sac do khi sang -> toi. Mau trung tinh dao nguoc hoan toan; mau co sac thai giu 500-600 du dam de nut bam
// (chu trang tren nen xanh) van doc duoc, con chu 600+ sang len de doc tren nen toi.
function darkShade(family, shade) {
  if (NEUTRAL.has(family)) return { 50: 950, 100: 900, 200: 800, 300: 700, 400: 500, 500: 400, 600: 300, 700: 200, 800: 100, 900: 50, 950: 50 }[shade];
  const m = { 50: 950, 100: 900, 200: 800, 300: 700, 400: 500, 500: 400, 600: family === "blue" ? 500 : 400, 700: 300, 800: 200, 900: 100, 950: 50 };
  return m[shade];
}

const rgb = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  return `${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255}`;
};

const themeColors = {};
const light = {};
const dark = {};
for (const f of FAMILIES) {
  themeColors[f] = {};
  for (const s of SHADES) {
    themeColors[f][s] = `rgb(var(--c-${f}-${s}) / <alpha-value>)`;
    light[`--c-${f}-${s}`] = rgb(colors[f][s]);
    dark[`--c-${f}-${s}`] = rgb(colors[f][darkShade(f, s)]);
  }
}

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: { extend: { colors: themeColors } },
  plugins: [
    plugin(({ addBase }) => {
      addBase({
        // che do sang phai tu khai bao la sang: neu khong, khi he dieu hanh dang toi, trinh duyet se dung nen toi + chu trang
        // lam mac dinh cho phan chua dat mau (loi hien thi khi bam ve giao dien sang)
        ":root": { ...light, colorScheme: "light" },
        ".dark": { ...dark, colorScheme: "dark" },
        // luu y: ten bien la sac do GOC (slate-50 = nen trang nhat); o che do toi gia tri cua no la mau toi
        ".dark body": { backgroundColor: "rgb(var(--c-slate-50))", color: "rgb(var(--c-slate-900))" },
        // o nhap/chon khong co bg-* thi lay nen toi cua the (:where giu do uu tien thap de bg-* van de duoc)
        ":where(.dark) :is(input, select, textarea)": { backgroundColor: "rgb(var(--c-slate-100))", color: "inherit" },
        // vien mac dinh cua Tailwind (gray-200) qua sang tren nen toi
        ".dark *, .dark ::before, .dark ::after": { borderColor: "rgb(var(--c-slate-200))" },
        // `bg-white` la be mat (the, thanh dieu huong, o nhap) nen dung mau nen toi; `text-white` van giu trang
        '.dark [class~="bg-white"]': { backgroundColor: "rgb(var(--c-slate-100))" },
      });
    }),
  ],
};
