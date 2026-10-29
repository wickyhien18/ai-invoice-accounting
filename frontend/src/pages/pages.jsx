// Gom toàn bộ export vào một nơi để App.jsx import cho dễ
import UploadPage from "./invoices/Upload.jsx";

export const Upload = UploadPage;
export { default as Review } from "./review/Review.jsx";
export { default as Entries } from "./entries/Entries.jsx";
export { default as Catalog } from "./catalog/Catalog.jsx";

// Các file chúng ta chuẩn bị tách ra:
export { default as Approvals } from "./approvals/Approvals.jsx";
export { default as PurchaseOrders } from "./po/PurchaseOrders.jsx";
export { default as Export } from "./export/Export.jsx";