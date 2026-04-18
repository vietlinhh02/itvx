import { getServerSession } from "next-auth"
import type { Route } from "next"
import Image from "next/image"
import { redirect } from "next/navigation"

import { DashboardSystemErrorState } from "@/components/dashboard/dashboard-system-error-state"
import { AppLink } from "@/components/navigation/app-link"
import { authOptions } from "@/lib/auth-options"
import { fetchDashboardJson } from "@/lib/dashboard-server"
import { formatVietnamDate, formatVietnamDateTime } from "@/lib/datetime"

type BackendUser = {
  id: string
  email: string
  name: string | null
  role: string
  is_active: boolean
}

type JDRecentItem = {
  jd_id: string
  file_name: string
  status: string
  created_at: string
  job_title: string | null
}

type ScreeningListItem = {
  screening_id: string
  jd_id: string
  candidate_id: string
  file_name: string
  created_at: string
  recommendation: "advance" | "review" | "reject"
  match_score: number
}

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

const RECOMMENDATION_STYLES: Record<ScreeningListItem["recommendation"], string> = {
  advance: "bg-emerald-50 text-emerald-700",
  review: "bg-sky-50 text-sky-700",
  reject: "bg-rose-50 text-rose-700",
}

const JD_STATUS_STYLES: Record<string, string> = {
  completed: "bg-emerald-50 text-emerald-700",
  processing: "bg-sky-50 text-sky-700",
  queued: "bg-amber-50 text-amber-700",
  failed: "bg-rose-50 text-rose-700",
}

const HERO_IMAGE_URL =
  "https://images.unsplash.com/photo-1744684182774-e6c61550c00e?auto=format&fit=crop&w=1800&q=80"

export default async function DashboardPage() {
  const session = await getServerSession(authOptions)

  if (!session?.accessToken) {
    redirect("/login")
  }

  if (!backendBaseUrl) {
    return (
      <DashboardSystemErrorState
        title="Không thể tải bảng điều khiển"
        description="Ứng dụng chưa được cấu hình địa chỉ backend. Hãy kiểm tra API_URL hoặc NEXT_PUBLIC_API_URL."
      />
    )
  }

  const [profileResult, recentJDResult, screeningsResult] = await Promise.all([
    fetchDashboardJson<BackendUser>({
      accessToken: session.accessToken,
      resourceLabel: "profile",
      url: `${backendBaseUrl}/api/v1/auth/me`,
    }),
    fetchDashboardJson<JDRecentItem[]>({
      accessToken: session.accessToken,
      resourceLabel: "recent JD uploads",
      url: `${backendBaseUrl}/api/v1/jd`,
    }),
    fetchDashboardJson<{ items: ScreeningListItem[] }>({
      accessToken: session.accessToken,
      resourceLabel: "screenings",
      url: `${backendBaseUrl}/api/v1/cv/screenings`,
    }),
  ])

  if (profileResult.kind === "auth" || recentJDResult.kind === "auth" || screeningsResult.kind === "auth") {
    redirect("/login")
  }

  if (
    profileResult.kind !== "success" ||
    recentJDResult.kind !== "success" ||
    screeningsResult.kind !== "success"
  ) {
    const failedResult = [profileResult, recentJDResult, screeningsResult].find((result) => result.kind !== "success")
    return (
      <DashboardSystemErrorState
        title="Không thể tải bảng điều khiển"
        description="Backend đang lỗi hoặc không phản hồi khi tải dữ liệu tổng quan."
        status={failedResult?.status}
      />
    )
  }

  const profile: BackendUser = profileResult.data
  const recentUploads: JDRecentItem[] = recentJDResult.data
  const screenings: ScreeningListItem[] = screeningsResult.data.items

  const recentJDItems = recentUploads.slice(0, 4)
  const recentScreenings = screenings.slice(0, 6)
  const reviewCount = screenings.filter((item) => item.recommendation === "review").length
  const completedJDCount = recentUploads.filter((item) => item.status === "completed").length
  const latestScreening = screenings[0] ?? null
  const topScreening = screenings.reduce<ScreeningListItem | null>((best, item) => {
    if (!best || item.match_score > best.match_score) {
      return item
    }
    return best
  }, null)
  const dominantRecommendation = getDominantRecommendation(screenings)

  return (
    <main className="flex w-full max-w-none flex-col gap-6 py-6">
      <section className="relative overflow-hidden rounded-[28px] shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <Image
          src={HERO_IMAGE_URL}
          alt="Blue sky and horizon background"
          fill
          className="object-cover blur-[2px] scale-[1.02]"
          priority
          sizes="100vw"
        />
        <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.9)_0%,rgba(255,255,255,0.8)_40%,rgba(235,246,255,0.74)_100%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.36),transparent_40%)]" />
        <div className="relative p-6 lg:p-8 xl:p-10">
          <div className="flex items-center justify-center py-2">
            <div className="grid w-full items-center gap-8 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)] xl:gap-12">
              <div className="w-full max-w-3xl">
                <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Tổng quan nhanh</p>
                <h1 className="mt-2 text-3xl font-semibold text-[var(--color-brand-text-primary)] lg:text-4xl xl:text-5xl">
                  Bảng điều khiển tuyển dụng
                </h1>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--color-brand-text-body)] lg:text-base">
                  Theo dõi tiến độ phân tích JD, sàng lọc CV và các đầu việc cần ưu tiên trong không gian làm việc hiện tại.
                </p>

                <div className="mt-6 grid w-full max-w-2xl gap-3 sm:grid-cols-2">
                  <SummaryPill label="Người dùng" value={profile.name ?? profile.email} />
                  <SummaryPill label="Vai trò" value={profile.role} />
                  <SummaryPill label="Trạng thái" value={profile.is_active ? "Đang hoạt động" : "Tạm khóa"} />
                  <SummaryPill label="Kết nối hệ thống" value="Backend đã kết nối" />
                </div>

                <div className="mt-6 flex flex-wrap gap-3">
                  <ActionLink href="/dashboard/jd">Mở khu vực phân tích JD</ActionLink>
                  <ActionLink href="/dashboard/cv-screenings" tone="secondary">
                    Mở lịch sử sàng lọc CV
                  </ActionLink>
                </div>
              </div>

              <div className="w-full xl:flex xl:justify-end">
                <div className="max-w-xl rounded-[24px] bg-white/30 p-5 backdrop-blur-[6px]">
                  <p className="text-2xl font-semibold italic text-[var(--color-brand-text-primary)]">
                    “Great teams are built one thoughtful decision at a time.”
                  </p>
                  <p className="mt-3 text-sm italic text-[var(--color-brand-text-body)]">
                    “The best hires are rarely the result of luck. They come from consistent judgment at every step.”
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="JD gần đây" value={String(recentUploads.length)} detail={`${completedJDCount} bản đã hoàn tất`} />
        <MetricCard label="Lượt sàng lọc CV" value={String(screenings.length)} detail={`${reviewCount} hồ sơ cần xem xét thêm`} />
        <MetricCard
          label="Hồ sơ nổi bật"
          value={topScreening ? `${Math.round(topScreening.match_score * 100)}%` : "—"}
          detail={topScreening ? topScreening.file_name : "Chưa có dữ liệu sàng lọc"}
        />
        <MetricCard
          label="Khuyến nghị phổ biến"
          value={dominantRecommendation ? dominantRecommendation.label : "—"}
          detail={dominantRecommendation ? `${dominantRecommendation.count} hồ sơ gần đây` : "Chưa có dữ liệu khuyến nghị"}
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]">
        <section className="overflow-hidden rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Hành động nhanh</p>
                <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
                  Bước tiếp theo nên làm
                </h2>
              </div>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <QuickActionCard
                href="/dashboard/jd"
                title="Tải và phân tích JD mới"
                description="Bắt đầu từ một mô tả công việc mới để tạo rubric và mở luồng sàng lọc ứng viên."
              />
              <QuickActionCard
                href="/dashboard/cv-screenings"
                title="Rà soát kết quả sàng lọc"
                description="Mở danh sách sàng lọc gần đây để kiểm tra các hồ sơ cần xem xét thêm hoặc có mức độ phù hợp cao."
              />
            </div>
        </section>

        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
          <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Tài khoản</p>
          <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">Thông tin phiên làm việc</h2>
          <dl className="mt-5 grid gap-3 text-sm">
            <InfoItem label="Mã người dùng" value={profile.id} />
            <InfoItem label="Email" value={profile.email} />
            <InfoItem label="Tên hiển thị" value={profile.name ?? "Không có"} />
            <InfoItem label="Vai trò" value={profile.role} />
            <InfoItem label="Trạng thái" value={profile.is_active ? "Đang hoạt động" : "Tạm khóa"} />
          </dl>
        </section>
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
          <div>
            <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">JD gần đây</p>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">Các JD tải lên gần đây</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">
              Truy cập nhanh các mô tả công việc mới nhất để tiếp tục phân tích hoặc sàng lọc.
            </p>
          </div>

          <div className="mt-5 flex flex-col gap-3">
            {recentJDItems.length ? (
              recentJDItems.map((item) => (
                <AppLink
                  className="rounded-[18px] border border-[var(--color-brand-input-border)] p-4 transition hover:border-[var(--color-brand-primary)] hover:bg-[var(--color-primary-50)]"
                  href={buildJDRoute(item.jd_id)}
                  key={item.jd_id}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-[var(--color-brand-text-primary)]">
                        {item.job_title ?? item.file_name}
                      </p>
                      <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.file_name}</p>
                    </div>
                    <span className={buildBadgeClass(JD_STATUS_STYLES[item.status] ?? "bg-slate-100 text-slate-700")}>
                      {formatJDStatus(item.status)}
                    </span>
                  </div>
                  <p className="mt-3 text-xs text-[var(--color-brand-text-muted)]">
                    {formatVietnamDateTime(item.created_at)}
                  </p>
                </AppLink>
              ))
            ) : (
              <EmptyPanel text="Chưa có JD nào được tải lên. Hãy bắt đầu bằng một mô tả công việc mới." />
            )}
          </div>
        </section>

        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
          <div>
            <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Sàng lọc gần đây</p>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">Kết quả sàng lọc gần đây</h2>
            <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">
              Theo dõi các hồ sơ ứng viên vừa được đánh giá để ưu tiên những trường hợp đáng chú ý.
            </p>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            {recentScreenings.length ? (
              recentScreenings.map((item) => (
                <AppLink
                  className="group rounded-[18px] border border-[var(--color-brand-input-border)] p-4 transition hover:border-[var(--color-brand-primary)] hover:bg-[var(--color-primary-50)]"
                  href={buildScreeningRoute(item.screening_id)}
                  key={item.screening_id}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className={buildBadgeClass(RECOMMENDATION_STYLES[item.recommendation])}>{formatRecommendation(item.recommendation)}</span>
                    <span className="text-xs font-semibold tabular-nums text-[var(--color-brand-primary)]">
                      {Math.round(item.match_score * 100)}%
                    </span>
                  </div>
                  <p className="mt-3 line-clamp-2 text-sm font-semibold text-[var(--color-brand-text-primary)]">
                    {item.file_name}
                  </p>
                  <p className="mt-2 text-xs text-[var(--color-brand-text-muted)]">
                    {formatVietnamDate(item.created_at)}
                  </p>
                </AppLink>
              ))
            ) : (
              <EmptyPanel text="Chưa có lượt sàng lọc nào. Hãy mở một JD và tải CV để bắt đầu." />
            )}
          </div>
        </section>
      </section>

      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <div>
          <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Nhận định nổi bật</p>
          <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">Gợi ý ưu tiên xử lý</h2>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-3">
          <InsightCard
            title="Khuyến nghị tiếp theo"
            description={
              recentUploads.length === 0
                ? "Hiện chưa có JD nào trong không gian làm việc. Ưu tiên tải lên một JD để bắt đầu quy trình tuyển dụng."
                : screenings.length === 0
                  ? "Bạn đã có JD nhưng chưa có lượt sàng lọc nào. Bước tiếp theo là tải CV từ trang chi tiết JD để tạo đánh giá ứng viên."
                  : "Dữ liệu JD và sàng lọc cơ bản đã có đủ. Bạn nên ưu tiên rà soát các hồ sơ cần xem xét thêm hoặc có mức độ phù hợp cao."
            }
          />
          <InsightCard
            title="Tín hiệu nổi bật"
            description={
              topScreening
                ? `Hồ sơ nổi bật nhất hiện tại đạt mức độ phù hợp ${Math.round(topScreening.match_score * 100)}% với tệp ${topScreening.file_name}.`
                : "Chưa có đủ dữ liệu để xác định hồ sơ nổi bật."
            }
          />
          <InsightCard
            title="Nhịp độ gần đây"
            description={
              latestScreening
                ? `Lượt sàng lọc mới nhất được tạo ngày ${formatVietnamDate(latestScreening.created_at)} với khuyến nghị ${formatRecommendation(latestScreening.recommendation)}.`
                : "Chưa có lượt sàng lọc nào được ghi nhận gần đây."
            }
          />
        </div>
      </section>
    </main>
  )
}

function ActionLink({
  href,
  children,
  tone = "primary",
}: {
  href: Route
  children: React.ReactNode
  tone?: "primary" | "secondary"
}) {
  return (
    <AppLink
      className={[
        "rounded-full px-4 py-2 text-sm font-semibold transition backdrop-blur-sm",
        tone === "primary"
          ? "bg-[var(--color-brand-primary)] text-white"
          : "border border-white/60 bg-white/70 text-[var(--color-brand-primary)]",
      ].join(" ")}
      href={href}
    >
      {children}
    </AppLink>
  )
}

function SummaryPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[18px] border border-white/60 bg-white/70 px-4 py-3 backdrop-blur-sm">
      <p className="text-xs text-[var(--color-brand-text-muted)]">{label}</p>
      <p className="mt-1 text-sm font-semibold text-[var(--color-brand-text-primary)]">{value}</p>
    </div>
  )
}

function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="rounded-[20px] bg-white p-5 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <p className="text-xs text-[var(--color-brand-text-muted)]">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-[var(--color-brand-text-primary)]">{value}</p>
      <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{detail}</p>
    </article>
  )
}

function QuickActionCard({
  href,
  title,
  description,
}: {
  href: Route
  title: string
  description: string
}) {
  return (
    <AppLink
      className="rounded-[20px] border border-[var(--color-brand-input-border)] p-5 transition hover:border-[var(--color-brand-primary)] hover:bg-[var(--color-primary-50)]"
      href={href}
    >
      <p className="text-base font-semibold text-[var(--color-brand-text-primary)]">{title}</p>
      <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">{description}</p>
    </AppLink>
  )
}

function InsightCard({ title, description }: { title: string; description: string }) {
  return (
    <article className="rounded-[20px] border border-[var(--color-brand-input-border)] p-5">
      <p className="text-base font-semibold text-[var(--color-brand-text-primary)]">{title}</p>
      <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">{description}</p>
    </article>
  )
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[16px] border border-[var(--color-brand-input-border)] bg-white p-4">
      <dt className="text-xs text-[var(--color-brand-text-muted)]">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-[var(--color-brand-text-primary)]">{value}</dd>
    </div>
  )
}

function EmptyPanel({ text }: { text: string }) {
  return (
    <p className="rounded-[18px] border border-dashed border-[var(--color-brand-input-border)] p-4 text-sm text-[var(--color-brand-text-muted)]">
      {text}
    </p>
  )
}

function buildBadgeClass(colorClass: string) {
  return ["rounded-full px-3 py-1 text-xs font-semibold", colorClass].join(" ")
}

function getDominantRecommendation(items: ScreeningListItem[]) {
  if (!items.length) {
    return null
  }

  const counts = items.reduce<Record<ScreeningListItem["recommendation"], number>>(
    (accumulator, item) => {
      accumulator[item.recommendation] += 1
      return accumulator
    },
    {
      advance: 0,
      review: 0,
      reject: 0,
    },
  )

  return (["advance", "review", "reject"] as const)
    .map((key) => ({ key, count: counts[key], label: formatRecommendation(key) }))
    .sort((left, right) => right.count - left.count)[0]
}

function buildJDRoute(jdId: string): Route {
  return `/dashboard/jd/${jdId}` as Route
}

function buildScreeningRoute(screeningId: string): Route {
  return `/dashboard/cv-screenings/${screeningId}` as Route
}

function formatRecommendation(recommendation: ScreeningListItem["recommendation"]) {
  if (recommendation === "advance") {
    return "Nên mời vào vòng tiếp theo"
  }
  if (recommendation === "review") {
    return "Cần xem xét thêm"
  }
  return "Không phù hợp để đi tiếp"
}

function formatJDStatus(status: string) {
  if (status === "completed") {
    return "Hoàn tất"
  }
  if (status === "processing") {
    return "Đang xử lý"
  }
  if (status === "queued") {
    return "Đang chờ"
  }
  if (status === "failed") {
    return "Thất bại"
  }

  return status
}
