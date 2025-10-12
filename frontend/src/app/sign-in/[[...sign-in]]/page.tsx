import { SignIn } from '@clerk/nextjs'

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-950 via-blue-950 to-purple-950 p-4">
      <SignIn 
        appearance={{
          elements: {
            rootBox: 'mx-auto',
            card: 'bg-gray-900 border border-gray-800',
          }
        }}
        routing="path"
        path="/sign-in"
      />
    </div>
  )
}

