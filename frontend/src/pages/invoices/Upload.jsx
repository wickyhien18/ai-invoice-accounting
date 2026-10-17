import { useRef, useState } from "react";
import { api } from "../../api/client.js";
import InvoiceList from "./InvoiceList.jsx";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.xml";
const MAX_MB = 10;

// Trang tai hoa don: keo tha nhieu file (PDF, anh, XML), tai tuan tu, roi hien danh sach va trang thai.
export default function Upload() {
  const [queue, setQueue] = useState([]);   // [{id, name, state: cho|dang_tai|xong|loi, msg}]
  const [refreshKey, setRefreshKey] = useState(0);
  const [over, setOver] = useState(false);
  const input = useRef(null);
  const busy = useRef(false);
  const nextId = useRef(1);

  const patch = (id, p) => setQueue((q) => q.map((x) => (x.id === id ? { ...x, ...p } : x)));

  async function uploadAll(files) {
    const items = files.map((file) => {
      const ext = file.name.split(".").pop().toLowerCase();
      const bad = !ACCEPT.includes(`.${ext}`) ? "Chỉ nhận PDF, PNG, JPG, XML"
        : file.size > MAX_MB * 1024 * 1024 ? `Lớn hơn ${MAX_MB} MB` : "";
      return { id: nextId.current++, file, name: file.name, state: bad ? "loi" : "cho", msg: bad };
    });
    setQueue((q) => [...items.map(({ file, ...rest }) => rest), ...q]);
    if (busy.current) return;           // dang tai dot truoc: dot nay se duoc xu ly boi vong lap hien tai
    busy.current = true;
    for (const it of items.filter((i) => i.state === "cho")) {
      patch(it.id, { state: "dang_tai" });
      try {
        const fd = new FormData();
        fd.append("file", it.file);
        await api("/api/invoices", { method: "POST", body: fd });
        patch(it.id, { state: "xong", msg: "Đã nhận, đang đọc dữ liệu" });
      } catch (e) {
        patch(it.id, { state: "loi", msg: e.message });
      }
      setRefreshKey((k) => k + 1);
    }
    busy.current = false;
  }

  const pick = (list) => list.length && uploadAll([...list]);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Tải hóa đơn</h1>
      <div
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files); }}
        onClick={() => input.current?.click()}
        role="button" tabIndex={0}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center ${over ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-white"}`}
      >
        <p className="font-medium">Kéo thả hóa đơn vào đây hoặc bấm để chọn</p>
        <p className="mt-1 text-sm text-slate-500">PDF, ảnh (PNG, JPG) hoặc XML hóa đơn điện tử · tối đa {MAX_MB} MB mỗi file · chọn được nhiều file</p>
        <input ref={input} type="file" multiple accept={ACCEPT} className="hidden"
          onChange={(e) => { pick(e.target.files); e.target.value = ""; }} />
      </div>

      {queue.length > 0 && (
        <ul className="space-y-1 text-sm">
          {queue.slice(0, 8).map((x) => (
            <li key={x.id} className="flex items-center gap-2 rounded border bg-white px-3 py-1.5">
              <span className="truncate">{x.name}</span>
              <span className={`ml-auto shrink-0 ${x.state === "loi" ? "text-red-600" : x.state === "xong" ? "text-green-700" : "text-slate-500"}`}>
                {x.state === "cho" ? "Đang chờ" : x.state === "dang_tai" ? "Đang tải…" : x.msg}
              </span>
            </li>
          ))}
        </ul>
      )}

      <InvoiceList refreshKey={refreshKey} />
    </div>
  );
}
