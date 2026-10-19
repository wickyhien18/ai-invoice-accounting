import { Link, Outlet, useNavigate } from "react-router-dom";

export default function MainLayout({ user, onLogout }) {
    const navigate = useNavigate();

    const handleLogout = () => {
        onLogout();
        navigate("/login");
    };

    return (
        <div className="flex h-screen bg-slate-50">
            {/* Sidebar (Thanh điều hướng bên trái) */}
            <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
                <div className="p-4 border-b border-slate-200">
                    <h1 className="text-xl font-bold text-blue-600">AI Invoice</h1>
                    {user && <p className="text-sm text-slate-500 mt-1">Xin chào, {user.email}</p>}
                </div>
                
                <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
                    {/* Các Link chuyển trang (sử dụng Tailwind để tạo nút) */}
                    <Link to="/upload" className="block px-4 py-2 rounded text-slate-700 hover:bg-slate-100 hover:text-blue-600">
                        Tải hóa đơn (A)
                    </Link>
                    <Link to="/review" className="block px-4 py-2 rounded text-slate-700 hover:bg-slate-100 hover:text-blue-600">
                        Kiểm tra trích xuất (B)
                    </Link>
                    <Link to="/entries" className="block px-4 py-2 rounded text-slate-700 hover:bg-slate-100 hover:text-blue-600">
                        Gợi ý định khoản (B)
                    </Link>
                    
                    <hr className="my-4 border-slate-200" />
                    
                    {/* Phần Menu của Gói C (của bạn) */}
                    <Link to="/approvals" className="block px-4 py-2 rounded font-medium text-blue-700 bg-blue-50">
                        Hàng chờ duyệt (C)
                    </Link>
                    <Link to="/purchase-orders" className="block px-4 py-2 rounded text-slate-700 hover:bg-slate-100 hover:text-blue-600">
                        Đơn mua hàng (PO)
                    </Link>
                    <Link to="/export" className="block px-4 py-2 rounded text-slate-700 hover:bg-slate-100 hover:text-blue-600">
                        Xuất bảng kê
                    </Link>
                </nav>

                <div className="p-4 border-t border-slate-200">
                    <button 
                        onClick={handleLogout}
                        className="w-full px-4 py-2 text-red-600 hover:bg-red-50 rounded font-medium text-left"
                    >
                        Đăng xuất
                    </button>
                </div>
            </aside>

            {/* Phần nội dung chính (Main Content) */}
            <main className="flex-1 overflow-y-auto p-8">
                {/* 
                    Component <Outlet /> là nơi React Router sẽ render (chèn) các trang con 
                    (Upload, Review, Approvals,...) tùy theo đường dẫn URL hiện tại.
                */}
                <Outlet />
            </main>
        </div>
    );
}