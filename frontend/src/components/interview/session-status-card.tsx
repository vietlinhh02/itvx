export function SessionStatusCard({
  status,
  workerStatus,
  providerStatus,
}: {
  status: string
  workerStatus: string
  providerStatus: string
}) {
  return (
    <section className="rounded-[24px] bg-white p-4 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Trạng thái phiên</p>
      <dl className="mt-3 grid gap-2 text-sm text-[var(--color-brand-text-body)]">
        <div className="flex justify-between gap-4">
          <dt>Phiên</dt>
          <dd>{status}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt>Worker</dt>
          <dd>{workerStatus}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt>Provider</dt>
          <dd>{providerStatus}</dd>
        </div>
      </dl>
    </section>
  )
}
