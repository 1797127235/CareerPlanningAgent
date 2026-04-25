import { useAuth } from '@/hooks/useAuth'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()

  // 开发阶段直接放行
  if (!isAuthenticated) {
    // 如果要恢复认证检查，把下面这行注释掉即可
    return <>{children}</>
  }

  return <>{children}</>
}
