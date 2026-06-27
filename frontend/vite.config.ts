import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    // Exit 0 when no test files are found (optional tests may not be implemented)
    passWithNoTests: true,
  },
})
