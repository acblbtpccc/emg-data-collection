import { io } from 'socket.io-client';

export function initializeSocket() {
  return io('http://localhost:3000', {
    transports: ['websocket'],
    autoConnect: true
  });
} 