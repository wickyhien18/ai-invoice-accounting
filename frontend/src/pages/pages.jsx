import Placeholder from "../components/Placeholder.jsx";
import UploadPage from "./invoices/Upload.jsx";

export const Upload = UploadPage; // Goi A (Hien): tai hoa don + danh sach + chi tiet
export const Review = () => <Placeholder title="Kiểm tra trường trích xuất" pkg="B" tasks="B3 (ảnh trái, trường phải, màu độ tin cậy)" />;
export const Entries = () => <Placeholder title="Bút toán gợi ý" pkg="B" tasks="B6, B7 (gợi ý Nợ/Có, lưu bút toán)" />;
export const Approvals = () => <Placeholder title="Hàng chờ duyệt" pkg="C" tasks="C3, C5 (duyệt/từ chối, cảnh báo bất thường)" />;
export const PurchaseOrders = () => <Placeholder title="Đơn mua hàng (PO)" pkg="C" tasks="C6, C7 (nhập PO, đối chiếu)" />;
export const Export = () => <Placeholder title="Xuất bảng kê" pkg="C" tasks="C4 (Excel / Google Sheet mẫu 01-2/GTGT)" />;
