# HrPayy — Hướng dẫn UI theo Figma (Hr Website UI Kit)

Tài liệu này bám theo file Figma **HrPayy - Hr Website UI Kit** để agent/code khớp layout, màu, typo và pattern component khi chỉnh `frontend/` (Next.js App Router, React 19, Tailwind CSS v4).

## Nguồn thiết kế (Figma)

- **File:** [HrPayy - Hr Website UI Kit](https://www.figma.com/design/snYhgvKDy4q5FzviXlaQrA/HrPayy---Hr-Website-UI-Kit)
- **fileKey:** `snYhgvKDy4q5FzviXlaQrA`

Các frame/node đã đối chiếu bằng MCP `get_design_context`:

| Mục đích | node-id (URL) | nodeId API |
|----------|----------------|------------|
| Trang đăng nhập (Sign in) | `118-2038` | `118:2038` |
| Landing desktop (Homepage 3) | `53-5` | `53:5` |
| Trang Blog / listing | `91-456` | `91:456` |
| Landing mobile | `101-566` | `101:566` |

Khi cần chi tiết pixel-perfect, gọi lại `get_design_context` với `fileKey` + `nodeId` tương ứng (đừng copy cứng code Tailwind từ Figma — chuyển sang token và utility của project).

## Stack hiện tại của `frontend/`

- Next.js 16, React 19, TypeScript
- Tailwind CSS v4 (`@import "tailwindcss"` trong `src/app/globals.css`)
- Font: Geist (Google) qua `layout.tsx` — **không trùng** bộ font trong Figma; khi cần sát design, cân nhắc thêm **Bricolage Grotesque**, **Afacad**, **DM Sans**, **Readex Pro**, **Satoshi** (theo chỗ dùng trong file)

## Token màu (từ frame đã export)

Dùng CSS variables trong `:root` hoặc `@theme inline` để map một lần, rồi dùng trong component.

| Token gợi ý | Hex | Ghi chú |
|-------------|-----|--------|
| `--color-text-primary` | `#12091e` | Tiêu đề, logo text, label chính |
| `--color-primary` | `#002043` | CTA chính (Sign in), accent, link brand |
| `--color-text-muted` | `#888e9e` | Divider text, meta phụ |
| `--color-text-placeholder` | `#6b7280` | Placeholder input, link phụ |
| `--color-text-body` | `#465264` | Footer links, body secondary (desktop landing) |
| `--color-surface-accent` | `#e6c1ff` | Nền pill/button nhẹ, khối trang trí |
| `--color-input-border` | `rgba(18,43,105,0.08)` | Viền input (stack shadow + ring trong design) |

Nền trang: trắng `#ffffff` hoặc off-white; section marketing có nền lavender nhạt / grid pattern (landing).

## Typography (theo Figma)

- **Display / hero lớn:** Bricolage Grotesque (SemiBold / ExtraBold), tracking âm nhẹ (ví dụ ~`-1.1px` trên size lớn).
- **Logo wordmark:** Satoshi Bold ~24px, tracking ~`-0.48px`.
- **Form & UI chữ thường:** Afacad Medium/SemiBold (label 18px, body 16px, line-height ~1.4).
- **Marketing body:** DM Sans Medium 16px line-height 1.5; Readex Pro cho một số dòng lớn; Inter cho style “Body/Small” trong blog.

Trong code: ưu tiên một **scale type** cố định (ví dụ `text-4xl` cho H1 marketing, `text-lg` label form) map về token thay vì hardcode font name trừ khi đã load font.

## Bo góc & đổ bóng

- **Card đăng nhập:** `rounded-[24px]`, shadow mềm: `0px 10px 30px rgba(15,79,87,0.06)` (tương đương trong Tailwind: arbitrary shadow).
- **Input / button phụ:** `rounded-[8px]`; input có shadow chồng mỏng (Figma: 2px/6px blur + ring 1px xanh đậm nhạt).
- **CTA primary:** nền `#002043`, chữ trắng, inner gloss (inset shadow xanh đậm).
- **Landing:** card / ảnh `rounded-[16px]`–`30px`; CTA pill `rounded-[50px]`.

## Pattern theo từng màn

### 1. Sign in (`118:2038`)

- Full viewport: nền có pattern + decorative image; **card trắng căn giữa** (~602×594px trong design).
- Khối: Logo → H1 "Sign in to HrPayy" → divider "Or Sign in with your gmail" → Email / Password (Forgot Password bên phải label) → nút Sign in → footer "Don’t have an account? Sign up".
- Input: height ~48px, padding ngang ~20px; password có control hiện/ẩn (trong Figma là ảnh — implement bằng button `type="button"` + text hoặc SVG tối thiểu, **không thêm bộ icon trang trí** nếu không bắt buộc).
- **Nội dung gốc có lỗi chính tả:** "Sing up" → sửa thành **"Sign up"** trong production.

### 2. Landing desktop (`53:5`)

- Header: logo trái, nav giữa (Home, Courses, Book a Demo, Info), phải Login + Get Started (nút đen/tốn).
- Hero: social proof sao + headline có highlight vàng brush; 2 CTA; mockup tablet bên phải; dải logo đối tác xám.
- Các section tiếp: showcase UI, talent + ảnh team, tabs tính năng + screenshot, grid "Unexpected HR Platform", block AI, testimonial carousel, CTA "Get your HrPayy on", FAQ accordion, footer 4 cột + legal + social.
- Màu nhấn brand `#002043`; vàng chart/accent như highlight hero (nếu có).

### 3. Blog listing (`91:456`)

- Header: About, Careers, How It Works, FAQ; Log in + Get Started pill tối.
- Breadcrumb "Home > Blogs"; H1 căn giữa; featured post full-bleed image + overlay text (date, category, title, author).
- Grid **3 cột** card: thumb, meta (năm · category), title, excerpt 2 dòng, author row.
- Container max-width ~1200–1280px căn giữa.

### 4. Landing mobile (`101:566`)

- Header: logo + hamburger.
- Cùng narrative với desktop nhưng cột đơn: hero → logo cloud → feature cards → list + mockup → grid testimonial → gradient CTA AI → quote lớn → FAQ accordion → footer nhiều cột (thu gọn trên mobile).

## Nguyên tắc triển khai trong repo này

1. **Bố cục:** ưu tiên flex/grid + `max-w-* mx-auto px-*`; tránh copy `absolute` pixel từ Figma trừ khi decorative.
2. **Tailwind:** dùng `@theme` / arbitrary values cho màu brand; giữ `globals.css` là nguồn token.
3. **Ảnh từ MCP:** URL `figma.com/api/mcp/asset/...` **hết hạn khoảng 7 ngày** — với production, export ảnh vào `public/` hoặc CDN và thay src.
4. **A11y:** heading hierarchy đúng; form có `<label htmlFor>`; nút bật password có `aria-pressed`; accordion FAQ dùng pattern button + `aria-expanded`.
5. **Chính tả trong design:** ngoài "Sign up", có "Attandance" → **"Attendance"** khi hiển thị cho user.

## Checklist nhanh trước khi merge UI

- [ ] Màu CTA và text primary khớp token `#002043` / `#12091e`
- [ ] Bo góc card form và input/button đúng cấp (24 / 8 / 50px theo context)
- [ ] Font scale và spacing không lệch quá so với frame tương ứng (Dev Mode trong Figma)
- [ ] Không phụ thuộc asset MCP tạm thời cho build production
- [ ] Đã sửa lỗi chính tả nội dung so với file gốc