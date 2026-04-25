import { createContext, useContext } from 'react'

export type ToastContextValue = {
  toast: (message: string) => void
}

export const ToastContext = createContext<ToastContextValue>({
  toast: () => {},
})

export function useToast() {
  return useContext(ToastContext)
}
