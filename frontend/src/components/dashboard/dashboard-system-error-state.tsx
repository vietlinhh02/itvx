type DashboardSystemErrorStateProps = {
  description: string
  status?: number
  title: string
}

export function DashboardSystemErrorState({
  description,
  status,
  title,
}: DashboardSystemErrorStateProps) {
  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <p className="text-sm font-medium text-amber-700">Lỗi hệ thống backend</p>
        <h1 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-[var(--color-brand-text-body)]">{description}</p>
        <p className="mt-4 rounded-[16px] border border-[var(--color-brand-input-border)] px-4 py-3 text-sm text-[var(--color-brand-text-muted)]">
          {status ? `Mã phản hồi backend: ${status}. ` : ""}
          Phiên đăng nhập của bạn vẫn còn hiệu lực. Vui lòng thử lại sau.
        </p>
      </section>
    </main>
  )
}
