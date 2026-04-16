import { defineConfig, globalIgnores } from "eslint/config"
import nextTs from "eslint-config-next/typescript.js"
import nextVitals from "eslint-config-next/core-web-vitals.js"

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
])

export default eslintConfig
