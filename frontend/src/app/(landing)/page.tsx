"use client"

import { 
  Sparkle, 
  Users, 
  Shield, 
  Lightning, 
  ArrowRight,
  VideoCamera,
  Calendar,
  FileText,
  Chats
} from "@phosphor-icons/react"
import { useAuthStore } from "@/stores/authStore"

export default function LandingPage() {
  const { loginWithGoogle, isLoading } = useAuthStore()

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 via-red-500 to-yellow-500 rounded-lg flex items-center justify-center">
                <Sparkle weight="fill" className="text-white" size={18} />
              </div>
              <span className="text-xl font-medium text-gray-900">InterviewX</span>
            </div>

            {/* Nav Links */}
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
                Tính năng
              </a>
              <a href="#how-it-works" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
                Cách hoạt động
              </a>
              <a href="#pricing" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
                Bảng giá
              </a>
            </div>

            {/* CTA Button */}
            <button
              onClick={loginWithGoogle}
              disabled={isLoading}
              className="px-5 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-full hover:bg-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Bắt đầu ngay
                  <ArrowRight size={16} weight="bold" />
                </>
              )}
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-20 pb-32 overflow-hidden">
        {/* Background Decoration */}
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full">
            <div className="absolute top-20 left-10 w-72 h-72 bg-blue-100 rounded-full mix-blend-multiply filter blur-3xl opacity-70 animate-blob" />
            <div className="absolute top-20 right-10 w-72 h-72 bg-purple-100 rounded-full mix-blend-multiply filter blur-3xl opacity-70 animate-blob animation-delay-2000" />
            <div className="absolute -bottom-8 left-1/2 w-72 h-72 bg-pink-100 rounded-full mix-blend-multiply filter blur-3xl opacity-70 animate-blob animation-delay-4000" />
          </div>
        </div>

        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-100 rounded-full mb-8">
            <Sparkle weight="fill" className="text-blue-600" size={16} />
            <span className="text-sm font-medium text-blue-700">Được hỗ trợ bởi Gemini AI</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-medium text-gray-900 leading-tight mb-6 max-w-4xl mx-auto">
            Tuyển dụng thông minh với
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              {" "}AI Interview
            </span>
          </h1>

          {/* Subheadline */}
          <p className="text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto mb-10 leading-relaxed">
            Để AI phỏng vấn, đánh giá và tuyển chọn ứng viên tự động. 
            Tiết kiệm 80% thởi gian tuyển dụng của bạn.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={loginWithGoogle}
              disabled={isLoading}
              className="w-full sm:w-auto px-8 py-4 bg-blue-600 text-white font-medium rounded-full hover:bg-blue-700 hover:shadow-lg hover:shadow-blue-600/25 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Dùng thử miễn phí
                  <ArrowRight size={20} weight="bold" />
                </>
              )}
            </button>
            <button className="w-full sm:w-auto px-8 py-4 bg-white text-gray-700 font-medium rounded-full border border-gray-300 hover:bg-gray-50 transition-all flex items-center justify-center gap-2">
              <VideoCamera size={20} />
              Xem demo
            </button>
          </div>

          {/* Trust Indicators */}
          <p className="mt-8 text-sm text-gray-500">
            Được tin dùng bởi 500+ công ty
          </p>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-medium text-gray-900 mb-4">
              Mọi thứ bạn cần để tuyển dụng hiệu quả
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Tích hợp đầy đủ công cụ từ sàng lọc CV đến phỏng vấn tự động
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mb-6">
                <Sparkle weight="fill" className="text-blue-600" size={24} />
              </div>
              <h3 className="text-xl font-medium text-gray-900 mb-3">
                AI Phỏng vấn tự động
              </h3>
              <p className="text-gray-600 leading-relaxed">
                5 agent AI chuyên biệt tự động phỏng vấn, đánh giá và xếp hạng ứng viên 24/7
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center mb-6">
                <Shield weight="fill" className="text-green-600" size={24} />
              </div>
              <h3 className="text-xl font-medium text-gray-900 mb-3">
                Sàng lọc CV thông minh
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Tự động phân tích CV, matching với job description và đánh giá độ phù hợp
              </p>
            </div>

            {/* Feature 3 */}
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mb-6">
                <Users weight="fill" className="text-purple-600" size={24} />
              </div>
              <h3 className="text-xl font-medium text-gray-900 mb-3">
                Phỏng vấn video trực tiếp
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Tích hợp video call, AI tương tác real-time bằng giọng nói tiếng Việt
              </p>
            </div>

            {/* Feature 4 */}
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center mb-6">
                <Calendar weight="fill" className="text-orange-600" size={24} />
              </div>
              <h3 className="text-xl font-medium text-gray-900 mb-3">
                Lên lịch tự động
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Tự động gửi email mời phỏng vấn và reminder cho ứng viên
              </p>
            </div>

            {/* Feature 5 */}
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-pink-100 rounded-xl flex items-center justify-center mb-6">
                <FileText weight="fill" className="text-pink-600" size={24} />
              </div>
              <h3 className="text-xl font-medium text-gray-900 mb-3">
                Báo cáo chi tiết
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Đánh giá đa chiều với rubric tự động và feedback cho từng competency
              </p>
            </div>

            {/* Feature 6 */}
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-cyan-100 rounded-xl flex items-center justify-center mb-6">
                <Lightning weight="fill" className="text-cyan-600" size={24} />
              </div>
              <h3 className="text-xl font-medium text-gray-900 mb-3">
                Tích hợp Google Workspace
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Đồng bộ với Gmail, Calendar và Drive của bạn
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-24 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-medium text-gray-900 mb-4">
              Quy trình tuyển dụng tự động
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Từ job description đến quyết định tuyển dụng chỉ trong vài phút
            </p>
          </div>

          <div className="grid md:grid-cols-5 gap-8">
            {[
              { step: "1", title: "Upload JD", desc: "Hệ thống phân tích yêu cầu" },
              { step: "2", title: "Sàng lọc", desc: "AI đánh giá CV tự động" },
              { step: "3", title: "Phỏng vấn", desc: "Video call với AI 24/7" },
              { step: "4", title: "Đánh giá", desc: "Báo cáo chi tiết tự động" },
              { step: "5", title: "Tuyển dụng", desc: "Quyết định dựa trên dữ liệu" },
            ].map((item, index) => (
              <div key={index} className="text-center">
                <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center text-lg font-medium mx-auto mb-4">
                  {item.step}
                </div>
                <h3 className="font-medium text-gray-900 mb-2">{item.title}</h3>
                <p className="text-sm text-gray-600">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gradient-to-br from-blue-600 to-purple-700">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-medium text-white mb-6">
            Sẵn sàng để tuyển dụng thông minh hơn?
          </h2>
          <p className="text-xl text-white/80 mb-10 max-w-2xl mx-auto">
            Bắt đầu dùng thử miễn phí 14 ngày. Không cần thẻ tín dụng.
          </p>
          <button
            onClick={loginWithGoogle}
            disabled={isLoading}
            className="px-8 py-4 bg-white text-blue-600 font-medium rounded-full hover:bg-gray-100 transition-all disabled:opacity-50 flex items-center justify-center gap-2 mx-auto"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-blue-600/30 border-t-blue-600 rounded-full animate-spin" />
            ) : (
              <>
                Bắt đầu miễn phí
                <ArrowRight size={20} weight="bold" />
              </>
            )}
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-gray-50 border-t border-gray-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 bg-gradient-to-br from-blue-500 via-red-500 to-yellow-500 rounded-md flex items-center justify-center">
                <Sparkle weight="fill" className="text-white" size={12} />
              </div>
              <span className="text-sm text-gray-600">© 2025 InterviewX</span>
            </div>
            <div className="flex items-center gap-6">
              <a href="#" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
                Chính sách bảo mật
              </a>
              <a href="#" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
                Điều khoản sử dụng
              </a>
              <a href="#" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
                Liên hệ
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
