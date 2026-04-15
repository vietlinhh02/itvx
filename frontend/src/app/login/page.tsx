"use client"

import { SignIn, GoogleLogo } from "@phosphor-icons/react"
import { useAuthStore } from "@/stores/authStore"

export default function LoginPage() {
  const { loginWithGoogle, isLoading, error } = useAuthStore()

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="p-3 bg-blue-600 rounded-lg">
              <SignIn weight="bold" size={28} className="text-white" />
            </div>
          </div>
          <h1 className="text-3xl font-medium text-gray-900">InterviewX</h1>
          <p className="mt-2 text-gray-600">Sign in to access your dashboard</p>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <button
          onClick={loginWithGoogle}
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-3 px-4 py-3 border border-gray-300 rounded-lg shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <div className="w-5 h-5 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin" />
          ) : (
            <GoogleLogo size={20} weight="bold" className="text-red-500" />
          )}
          <span>{isLoading ? "Signing in..." : "Continue with Google"}</span>
        </button>

        <p className="text-center text-sm text-gray-500">
          Only authorized HR and Admin accounts can access this system.
        </p>
      </div>
    </div>
  )
}
