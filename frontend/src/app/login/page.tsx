"use client"

import { Sparkle, ArrowLeft, GoogleLogo } from "@phosphor-icons/react"
import { useAuthStore } from "@/stores/authStore"
import Link from "next/link"

export default function LoginPage() {
  const { loginWithGoogle, isLoading, error } = useAuthStore()

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 flex flex-col">
      {/* Back to Home Link */}
      <div className="p-6">
        <Link 
          href="/" 
          className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft size={18} />
          Quay lại trang chủ
        </Link>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center px-4 sm:px-6 -mt-16">
        <div className="w-full max-w-md">
          {/* Login Card */}
          <div className="bg-white rounded-2xl shadow-xl shadow-gray-200/50 border border-gray-100 p-8 sm:p-10">
            {/* Logo & Header */}
            <div className="text-center mb-8">
              <div className="flex items-center justify-center gap-2 mb-6">
                <div className="w-12 h-12 bg-gradient-to-br from-blue-500 via-red-500 to-yellow-500 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/25">
                  <Sparkle weight="fill" className="text-white" size={24} />
                </div>
              </div>
              <h1 className="text-2xl font-medium text-gray-900 mb-2">
                Đăng nhập vào InterviewX
              </h1>
              <p className="text-gray-600">
                Tiếp tục với tài khoản Google của bạn
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-xl">
                <p className="text-sm text-red-600 font-medium">{error}</p>
              </div>
            )}

            {/* Google Sign In Button */}
            <button
              onClick={loginWithGoogle}
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-3 px-6 py-4 bg-white border border-gray-300 rounded-xl text-gray-700 font-medium hover:bg-gray-50 hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin" />
              ) : (
                <div className="flex items-center justify-center w-6 h-6">
                  <GoogleLogo 
                    size={22} 
                    weight="bold" 
                    className="text-red-500 group-hover:scale-110 transition-transform" 
                  />
                </div>
              )}
              <span>
                {isLoading ? "Đang đăng nhập..." : "Tiếp tục với Google"}
              </span>
            </button>

            {/* Divider */}
            <div className="relative my-8">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-white text-gray-500">
                  hoặc
                </span>
              </div>
            </div>

            {/* Demo Account */}
            <div className="text-center">
              <p className="text-sm text-gray-600 mb-4">
                Chưa có tài khoản?
              </p>
              <button
                onClick={loginWithGoogle}
                disabled={isLoading}
                className="w-full px-6 py-3 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 hover:shadow-lg hover:shadow-blue-600/25 transition-all disabled:opacity-50"
              >
                Tạo tài khoản mới
              </button>
            </div>
          </div>

          {/* Footer Info */}
          <div className="mt-8 text-center">
            <div className="flex items-center justify-center gap-2 mb-3">
              <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                </svg>
              </div>
              <span className="text-sm font-medium text-gray-700">Bảo mật cao</span>
            </div>
            <p className="text-xs text-gray-500 max-w-xs mx-auto">
              Chỉ tài khoản HR và Admin được cấp quyền mới có thể truy cập hệ thống.
              Mọi hoạt động đều được mã hóa và bảo vệ.
            </p>
          </div>

          {/* Links */}
          <div className="mt-6 flex items-center justify-center gap-6 text-xs text-gray-500">
            <a href="#" className="hover:text-gray-700 transition-colors">
              Chính sách bảo mật
            </a>
            <span className="text-gray-300">|</span>
            <a href="#" className="hover:text-gray-700 transition-colors">
              Điều khoản sử dụng
            </a>
            <span className="text-gray-300">|</span>
            <a href="#" className="hover:text-gray-700 transition-colors">
              Trợ giúp
            </a>
          </div>
        </div>
      </div>

      {/* Background Decoration */}
      <div className="fixed inset-0 -z-10 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-0 w-96 h-96 bg-blue-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob" />
        <div className="absolute top-1/4 right-0 w-96 h-96 bg-purple-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000" />
        <div className="absolute -bottom-32 left-1/2 w-96 h-96 bg-pink-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000" />
      </div>
    </div>
  )
}
