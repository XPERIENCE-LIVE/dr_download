import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import DownloadPanel from '../components/DownloadPanel';
import axios from 'axios';

jest.mock('axios');

describe('DownloadPanel', () => {
  beforeEach(() => {
    globalThis.importMetaEnv = { VITE_API_BASE_URL: 'http://localhost:8000' };
    axios.post.mockReset();
    axios.get.mockReset();
    window.electronAPI = { selectFolder: jest.fn(() => Promise.resolve('/tmp/out')) };
  });

  test('select folder updates output field', async () => {
    render(<DownloadPanel />);
    fireEvent.click(screen.getByText('Choose...'));
    await waitFor(() => expect(window.electronAPI.selectFolder).toHaveBeenCalled());
    expect(screen.getByPlaceholderText('Output folder').value).toBe('/tmp/out');
  });

  test('start download posts to API and shows progress button', async () => {
    axios.post.mockResolvedValue({ data: { task_id: '123' } });
    render(<DownloadPanel />);
    fireEvent.change(screen.getByPlaceholderText('YouTube or playlist URL'), { target: { value: 'https://example.com' } });
    fireEvent.change(screen.getByPlaceholderText('Output folder'), { target: { value: '/tmp/out' } });
    fireEvent.click(screen.getByText('Start Download'));
    await waitFor(() => expect(axios.post).toHaveBeenCalled());
    expect(axios.post).toHaveBeenCalledWith('http://localhost:8000/download/', {
      url: 'https://example.com',
      format: 'video',
      output_dir: '/tmp/out'
    });
    expect(screen.getByText('Check Progress')).toBeInTheDocument();
  });

  test('check progress fetches and displays progress', async () => {
    axios.post.mockResolvedValue({ data: { task_id: '123' } });
    axios.get.mockResolvedValue({ data: { progress: 42 } });
    render(<DownloadPanel />);
    fireEvent.change(screen.getByPlaceholderText('YouTube or playlist URL'), { target: { value: 'https://example.com' } });
    fireEvent.change(screen.getByPlaceholderText('Output folder'), { target: { value: '/tmp/out' } });
    fireEvent.click(screen.getByText('Start Download'));
    await waitFor(() => screen.getByText('Check Progress'));
    fireEvent.click(screen.getByText('Check Progress'));
    await waitFor(() => expect(axios.get).toHaveBeenCalledWith('http://localhost:8000/progress/123'));
    expect(screen.getByText('Progress: 42%')).toBeInTheDocument();
  });
});
