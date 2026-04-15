# Frontend Design Guidelines

## Philosophy

Thiết kế theo phong cách Google Material Design 3: clean, minimal, consistent, và functional. UI phải professional phù hợp cho HR/Admin sử dụng hàng ngày.

## Icon System

**KHÔNG DÙNG EMOJI** - Chỉ dùng icons từ [Phosphor Icons](https://phosphoricons.com/)

### Installation

```bash
cd frontend
pnpm add @phosphor-icons/react
```

### Usage

```tsx
import { SignIn, User, Gear, House, ChartBar } from "@phosphor-icons/react"

// Default (regular weight)
<SignIn size={20} />

// Different weights
<User weight="bold" size={24} />
<Gear weight="fill" size={20} />

// With color
<ChartBar size={32} className="text-blue-600" />
```

### Icon Mapping (Common Actions)

| Action | Icon | Weight |
|--------|------|--------|
| Login/Sign In | `SignIn` | regular |
| Logout/Sign Out | `SignOut` | regular |
| User/Profile | `User`, `UserCircle` | regular |
| Settings | `Gear` | regular |
| Home/Dashboard | `House` | regular |
| Analytics/Charts | `ChartBar`, `ChartLineUp` | regular |
| Search | `MagnifyingGlass` | regular |
| Add/New | `Plus` | bold |
| Edit | `Pencil` | regular |
| Delete | `Trash` | regular |
| Save | `FloppyDisk` | regular |
| Close/X | `X` | regular |
| Menu/Hamburger | `List` | regular |
| Notification | `Bell` | regular |
| Calendar | `Calendar` | regular |
| Clock/Time | `Clock` | regular |
| Check/Done | `Check` | bold |
| Warning | `Warning` | fill |
| Error | `XCircle` | fill |
| Info | `Info` | regular |
| More Options | `DotsThree` | regular |
| Filter | `Faders` | regular |
| Sort | `ArrowsDownUp` | regular |
| Upload | `Upload` | regular |
| Download | `Download` | regular |
| Refresh | `ArrowsClockwise` | regular |
| Link/External | `ArrowSquareOut` | regular |
| Back | `ArrowLeft` | regular |
| Forward | `ArrowRight` | regular |
| Interview | `VideoCamera` | regular |
| Candidates | `Users` | regular |
| Jobs/Positions | `Briefcase` | regular |
| Documents | `FileText` | regular |
| Email | `Envelope` | regular |
| Phone | `Phone` | regular |
| Location | `MapPin` | regular |
| Star/Rating | `Star` | fill |
| AI/Spark | `Sparkle` | regular |

## Color Palette (Google Style)

```css
/* Primary - Google Blue */
--color-primary: #1a73e8;
--color-primary-hover: #1557b0;
--color-primary-light: #e8f0fe;

/* Surface Colors */
--color-surface: #ffffff;
--color-surface-variant: #f8f9fa;
--color-background: #f1f3f4;

/* Text Colors */
--color-text-primary: #202124;
--color-text-secondary: #5f6368;
--color-text-tertiary: #80868b;

/* Border/Divider */
--color-border: #dadce0;
--color-divider: #e8eaed;

/* Status Colors */
--color-success: #34a853;
--color-warning: #fbbc04;
--color-error: #ea4335;
--color-info: #4285f4;
```

## Typography

- **Font Family**: System font stack (default Tailwind)
- **Headings**: font-weight 500 (medium)
- **Body**: font-weight 400 (normal)
- **No ALL CAPS** cho headings

## Spacing & Layout

- **Container max-width**: 1280px (max-w-7xl)
- **Card padding**: 24px (p-6)
- **Section gap**: 24px (space-y-6, gap-6)
- **Element gap**: 16px (gap-4)
- **Border radius**: 8px cho cards (rounded-lg), 4px cho buttons nhỏ

## Components

### Buttons

```tsx
// Primary Button
<button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium">
  <Plus weight="bold" className="inline mr-2" size={18} />
  New Interview
</button>

// Secondary Button
<button className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
  Cancel
</button>

// Text Button
<button className="px-2 py-1 text-blue-600 hover:bg-blue-50 rounded transition-colors">
  View details
</button>

// Icon Button
<button className="p-2 text-gray-600 hover:bg-gray-100 rounded-full transition-colors">
  <Gear size={20} />
</button>
```

### Cards

```tsx
// Standard Card
<div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
  <div className="flex items-center gap-3 mb-4">
    <div className="p-2 bg-blue-100 rounded-lg">
      <Users size={24} className="text-blue-600" />
    </div>
    <div>
      <h3 className="font-medium text-gray-900">Total Candidates</h3>
      <p className="text-2xl font-semibold text-gray-900">128</p>
    </div>
  </div>
</div>
```

### Navigation

```tsx
// Sidebar Item (Active)
<a className="flex items-center gap-3 px-4 py-3 bg-blue-50 text-blue-700 rounded-lg">
  <House weight="fill" size={20} />
  <span className="font-medium">Dashboard</span>
</a>

// Sidebar Item (Inactive)
<a className="flex items-center gap-3 px-4 py-3 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
  <Users size={20} />
  <span>Candidates</span>
</a>
```

### Forms

```tsx
// Input Field
<div className="space-y-2">
  <label className="text-sm font-medium text-gray-700">Email</label>
  <div className="relative">
    <Envelope size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
    <input 
      type="email" 
      className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      placeholder="Enter email"
    />
  </div>
</div>
```

### Tables

```tsx
<table className="w-full">
  <thead className="bg-gray-50 border-b border-gray-200">
    <tr>
      <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Name</th>
      <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Status</th>
      <th className="px-4 py-3 text-left text-sm font-medium text-gray-600">Actions</th>
    </tr>
  </thead>
  <tbody className="divide-y divide-gray-200">
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 text-sm text-gray-900">John Doe</td>
      <td className="px-4 py-3">
        <span className="inline-flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-green-700 bg-green-100 rounded-full">
          <CheckCircle size={12} weight="fill" />
          Active
        </span>
      </td>
      <td className="px-4 py-3">
        <button className="p-1 text-gray-400 hover:text-gray-600">
          <DotsThree size={20} />
        </button>
      </td>
    </tr>
  </tbody>
</table>
```

## Page Layouts

### Login Page
- Centered card
- Clean background (gray-50)
- Google logo + "Continue with Google" button
- No decorative elements

### Dashboard
- Header: Logo left, user info right
- Main content: Cards in grid layout
- Stats overview at top
- Recent activity/section below

### List Pages (Candidates, Jobs)
- Search bar + filters at top
- Table or card grid below
- Pagination at bottom

## Animations

Keep animations subtle and purposeful:

```css
/* Button hover */
transition-colors duration-200

/* Card hover */
transition-shadow duration-200 hover:shadow-md

/* Page transitions */
transition-opacity duration-300
```

**No bouncy animations, no excessive transitions.**

## Responsive Breakpoints

```
mobile: < 640px (default)
tablet: 640px - 1024px (sm:, md:)
desktop: > 1024px (lg:, xl:)
```

## State Management with Zustand

**KHÔNG DÙNG useEffect** - Luôn dùng Zustand cho state management

### Installation

```bash
cd frontend
pnpm add zustand
```

### Store Pattern

```tsx
// stores/authStore.ts
import { create } from "zustand"

interface AuthState {
  // State
  isLoading: boolean
  error: string | null
  user: User | null
  
  // Actions
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setUser: (user: User | null) => void
  login: () => Promise<void>
  logout: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  isLoading: false,
  error: null,
  user: null,
  
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  setUser: (user) => set({ user }),
  
  login: async () => {
    set({ isLoading: true, error: null })
    try {
      // API call logic
      const user = await api.login()
      set({ user, isLoading: false })
    } catch (error) {
      set({ error: error.message, isLoading: false })
    }
  },
  
  logout: async () => {
    set({ isLoading: true })
    try {
      await api.logout()
      set({ user: null, isLoading: false })
    } catch (error) {
      set({ error: error.message, isLoading: false })
    }
  },
}))
```

### Usage in Components

```tsx
// Good: Use Zustand store
"use client"

import { useAuthStore } from "@/stores/authStore"

export default function LoginButton() {
  const { login, isLoading } = useAuthStore()
  
  return (
    <button onClick={login} disabled={isLoading}>
      {isLoading ? "Loading..." : "Login"}
    </button>
  )
}
```

```tsx
// Bad: Using useEffect for side effects
"use client"

import { useEffect, useState } from "react" // ❌ DON'T

export default function BadComponent() {
  const [data, setData] = useState(null) // ❌ DON'T
  
  useEffect(() => { // ❌ DON'T - Avoid useEffect
    fetchData().then(setData)
  }, [])
  
  return <div>{data}</div>
}
```

### When to use Zustand

| Use Case | Solution |
|----------|----------|
| Form state | Zustand store |
| API calls | Zustand actions |
| UI state (modal, sidebar) | Zustand store |
| User auth state | Zustand store |
| Loading states | Zustand store |

### Store Organization

```
stores/
├── authStore.ts       # Authentication state
├── uiStore.ts         # UI state (modals, sidebar)
├── interviewStore.ts  # Interview-related state
└── index.ts           # Re-exports
```

### Rules

1. **Mọi component phải là Client Component** (`"use client"`) nếu cần interactivity
2. **Không dùng useEffect** cho data fetching hay side effects
3. **Luôn dùng Zustand actions** thay vì useEffect
4. **Select only what you need** từ store để tránh re-renders

```tsx
// Good: Select specific state
const user = useAuthStore((state) => state.user)

// Bad: Select entire store (causes re-renders)
const store = useAuthStore() // ❌ DON'T
```

## Do's and Don'ts

### DO
- Use consistent spacing (multiples of 4)
- Use subtle shadows (shadow-sm, shadow)
- Use meaningful icons from Phosphor
- Use semantic HTML
- Provide hover states
- Use loading skeletons
- **Use Zustand for all state management**
- **Use Client Components with Zustand**

### DON'T
- Use emojis
- Use gradients for backgrounds
- Use shadows > shadow-md
- Use ALL CAPS for text
- Use more than 3 font weights on a page
- Use borders heavier than 1px
- Use arbitrary values (e.g., w-[123px])
- **Use useEffect (hạn chế tối đa)**
- **Use Server Actions cho interactive features**

## Example: Complete Page Structure

```tsx
// app/dashboard/page.tsx
import { House, Users, Briefcase, ChartBar } from "@phosphor-icons/react"

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-medium text-gray-900">Dashboard</h1>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
          <Plus weight="bold" className="inline mr-2" size={18} />
          New Job
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard 
          icon={Users} 
          label="Total Candidates" 
          value="128"
          trend="up"
          trendValue="12%"
        />
        <StatCard 
          icon={Briefcase} 
          label="Active Jobs" 
          value="8"
        />
        <StatCard 
          icon={ChartBar} 
          label="Interviews Today" 
          value="5"
        />
      </div>

      {/* Main Content */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="font-medium text-gray-900">Recent Activity</h2>
        </div>
        <div className="p-6">
          {/* Content */}
        </div>
      </div>
    </div>
  )
}

// Component: StatCard
function StatCard({ icon: Icon, label, value, trend, trendValue }) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-start justify-between">
        <div className="p-2 bg-blue-50 rounded-lg">
          <Icon size={24} className="text-blue-600" />
        </div>
        {trend && (
          <span className={`text-sm font-medium ${
            trend === 'up' ? 'text-green-600' : 'text-red-600'
          }`}>
            {trend === 'up' ? '+' : '-'}{trendValue}
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-sm text-gray-600">{label}</p>
        <p className="text-2xl font-semibold text-gray-900">{value}</p>
      </div>
    </div>
  )
}
```
