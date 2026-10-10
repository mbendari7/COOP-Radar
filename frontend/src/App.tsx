import { Route, Routes } from 'react-router-dom'
import PostingDetailPage from './pages/PostingDetailPage'
import PostingsListPage from './pages/PostingsListPage'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        <Route path="/" element={<PostingsListPage />} />
        <Route path="/postings/:id" element={<PostingDetailPage />} />
      </Routes>
    </div>
  )
}
