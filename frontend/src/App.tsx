import { Route, Routes } from 'react-router-dom'
import { DealList } from './pages/DealList'
import { DealNew } from './pages/DealNew'
import { DealDetail } from './pages/DealDetail'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<DealList />} />
      <Route path="/deals/new" element={<DealNew />} />
      <Route path="/deals/:id" element={<DealDetail />} />
    </Routes>
  )
}
