import { Route, Routes } from 'react-router-dom';

import IndexPage from '@/pages/index';
import HistoryPage from './pages/history';
import ManualPage from './pages/manual';

function App() {
  return (
    <Routes>
      <Route element={<IndexPage />} path="/" />
      <Route element={<HistoryPage />} path="/history/:key" />
      <Route element={<ManualPage />} path="/manual" />
    </Routes>
  );
}

export default App;
