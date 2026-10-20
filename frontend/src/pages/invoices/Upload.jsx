import { useEffect, useRef, useState } from "react";
import { api, uploadWithProgress } from "../../api/client.js";
import InvoiceList from "./InvoiceList.jsx";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,.xml";
const MAX_MB = 10;
const UPLOAD_SHARE = 25;        // thanh tien do: 0-25% la tai len, 25-100% la he thong doc du lieu
const SUCCESS_SHOW_MS = 8000;   // thong bao thanh cong hien vai giay roi tu mat
const POLL_MS = 1000;
const POLL_LIMIT_MS = 5 * 60 * 1000;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Trang tai hoa don: keo tha nhieu file (PDF, anh, XML), tai tuan tu, roi hien danh sach va trang thai.
export default function Upload() {
  const [queue, setQueue] = useState([]);   // [{id, name, state: cho|dang_tai|xong|loi, msg}]
  const [refreshKey, setRefreshKey] = useState(0);
  const [over, setOver] = useState(false);
  const input = useRef(null);
  const busy = useRef(false);
  const nextId = useRef(1);
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);

  const patch = (id, p) => setQueue((q) => q.map((x) => (x.id === id ? { ...x, ...p } : x)));

  // Hoi tien do doc du lieu cua mot hoa don cho den khi xong; chay song song, khong chan viec tai file tiep theo.
  async function watch(id, invoiceId) {
    const t0 = Date.now();
    let fails = 0;
    while (alive.current && Date.now() - t0 < POLL_LIMIT_MS) {
      try {
        const { data } = await api(`/api/invoices/${invoiceId}/progress`);
        fails = 0;
        if (data.status !== "dang_xu_ly") {
          if (data.status === "loi_xu_ly") {
            patch(id, { state: "loi", msg: "Không đọc được hóa đơn (dịch vụ AI tắt hoặc hết hạn mức). Vào danh sách bấm “Xử lý lại”." });
          } else {
            patch(id, { state: "xong", msg: "Đọc dữ liệu thành công" });
            setTimeout(() => alive.current && setQueue((q) => q.filter((x) => x.id !== id)), SUCCESS_SHOW_MS);
          }
          setRefreshKey((k) => k + 1);
          return;
        }
        patch(id, { state: "dang_doc", percent: UPLOAD_SHARE + Math.round((data.percent * (100 - UPLOAD_SHARE)) / 100), stage: data.stage });
      } catch {
        if (++fails >= 5) break;
      }
      await sleep(POLL_MS);
    }
    if (alive.current) patch(id, { state: "xong", msg: "Đã nhận; xem kết quả trong danh sách bên dưới" });
  }

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
      patch(it.id, { state: "dang_tai", percent: 0, stage: "Đang tải lên" });
      try {
        const fd = new FormData();
        fd.append("file", it.file);
        const { data } = await uploadWithProgress("/api/invoices", fd,
          (p) => patch(it.id, { percent: Math.round((p * UPLOAD_SHARE) / 100) }));
        if (data.status === "dang_xu_ly") {
          patch(it.id, { state: "dang_doc", percent: UPLOAD_SHARE, stage: "Đã nhận, đang chờ xử lý" });
          watch(it.id, data.invoice_id);            // khong await: tai file ke tiep ngay
        } else if (data.status === "loi_xu_ly") {
          patch(it.id, { state: "loi", msg: "Không đọc được hóa đơn" });
        } else {                                    // XML: doc xong ngay khi tai len
          patch(it.id, { state: "xong", msg: "Đọc dữ liệu thành công" });
          setTimeout(() => alive.current && setQueue((q) => q.filter((x) => x.id !== it.id)), SUCCESS_SHOW_MS);
        }
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
          {queue.slice(0, 8).map((x) => {
            const working = x.state === "dang_tai" || x.state === "dang_doc";
            return (
              <li key={x.id} className="rounded border bg-white px-3 py-1.5">
                <div className="flex items-center gap-2">
                  <span className="truncate">{x.name}</span>
                  <span className={`ml-auto shrink-0 ${x.state === "loi" ? "text-red-600" : x.state === "xong" ? "text-green-700" : "text-slate-500"}`}>
                    {x.state === "cho" ? "Đang chờ"
                      : working ? `${x.stage} · ${x.percent}%`
                      : x.state === "xong" ? `✓ ${x.msg}` : x.msg}
                  </span>
                </div>
                {working && (
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-200" role="progressbar"
                    aria-valuemin={0} aria-valuemax={100} aria-valuenow={x.percent} aria-label={`Tiến độ ${x.name}`}>
                    <div className="h-full rounded-full bg-blue-600 transition-all duration-500" style={{ width: `${x.percent}%` }} />
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <InvoiceList refreshKey={refreshKey} />
    </div>
  );
}
