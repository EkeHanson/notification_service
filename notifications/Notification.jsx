import React, { useState, useEffect, useRef } from 'react';
import {
  EnvelopeIcon,
  EnvelopeOpenIcon,
  ArrowLeftIcon,
} from "@heroicons/react/24/outline";
import { motion, AnimatePresence } from "framer-motion";
import { fetchInAppMessages, markMessageAsRead } from './Employees/config/apiService';
import { WEBSOCKET_URL } from '../../config';




const Notification = ({ onUnreadChange }) => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Fetch notifications from API
  const fetchNotifications = async () => {
    try {
      const data = await fetchInAppMessages({ limit: 50 });
      if (data && data.results) {
        setNotifications(data.results);
      }
    } catch (error) {
      console.warn('Notification API not available yet:', error.message);
      // Set empty notifications - feature not implemented on backend yet
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  };


  
  // WebSocket connection for real-time notifications
  const connectWebSocket = () => {
    try {
      const token = localStorage.getItem('accessToken');
      const tenantId = localStorage.getItem('tenantId');

      if (!token || !tenantId) {
        console.warn('No token or tenant ID found for WebSocket connection');
        return;
      }

      // Route WebSocket connections through API Gateway
      // Gateway URL should be: ws://localhost:9090/ws/notifications/{tenantId}/?token={token}
      const wsUrl = `${WEBSOCKET_URL}/ws/notifications/${tenantId}/?token=${token}`;

      console.log('Connecting to WebSocket through gateway:', wsUrl.substring(0, 100) + '...');

      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connected for notifications');
        setIsConnected(true);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log('WebSocket message received:', message.type);
          handleWebSocketMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        // Try to reconnect after a delay
        scheduleReconnect();
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        // Try to reconnect after a delay
        scheduleReconnect();
      };

    } catch (error) {
      console.error('WebSocket connection setup failed:', error);
      // Try to reconnect after a delay
      scheduleReconnect();
    }
  };

  const scheduleReconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    reconnectTimeoutRef.current = setTimeout(() => {
      console.log('Attempting to reconnect WebSocket...');
      connectWebSocket();
    }, 5000);
  };

  const handleWebSocketMessage = (message) => {
    switch (message.type) {
      case 'notification':
        // Add new notification to the list
        setNotifications(prev => [message, ...prev]);
        break;
      case 'connection_established':
        console.log('WebSocket connection confirmed');
        break;
      default:
        console.log('Unknown message type:', message.type);
    }
  };

  // Mark notification as read
  const handleNotificationClick = async (notification) => {
    if (!notification.read_at) {
      try {
        await markMessageAsRead(notification.id);
        // Update local state
        setNotifications(prev =>
          prev.map(n =>
            n.id === notification.id ? { ...n, read_at: new Date().toISOString() } : n
          )
        );
      } catch (error) {
        console.warn('Mark as read API not available yet:', error.message);
        // Still update local state optimistically
        setNotifications(prev =>
          prev.map(n =>
            n.id === notification.id ? { ...n, read_at: new Date().toISOString() } : n
          )
        );
      }
    }
    setSelectedNotification(notification);
  };

  const handleBack = () => setSelectedNotification(null);

  // Format date for display
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  };

  // Group notifications by date
  // const groupedNotifications = notifications.reduce((acc, notif) => {
  //   const date = formatDate(notif.sent_at);
  //   if (!acc[date]) acc[date] = [];
  //   acc[date].push({
  //     ...notif,
  //     date,
  //     time: formatTime(notif.sent_at),
  //     message: notif.body
  //   });
  //   return acc;
  // }, {});

    // Group notifications by date - FIXED: Use created_at only
  const groupedNotifications = notifications.reduce((acc, notif) => {
    const displayDate = notif.created_at; // Use created_at directly
    const date = formatDate(displayDate);
    
    if (!acc[date]) acc[date] = [];
    acc[date].push({
      ...notif,
      formattedDate: date,
      formattedTime: formatTime(displayDate),
      message: notif.body || notif.message
    });
    return acc;
  }, {});


  // Calculate unread count
  useEffect(() => {
    const unreadCount = notifications.filter(n => !n.read_at).length;
    onUnreadChange(unreadCount);
  }, [notifications, onUnreadChange]);

  // Initialize
  useEffect(() => {
    fetchNotifications();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  if (loading) {
    return (
      <div className="Notification-Main custom-scroll-bar">
        <div className="loading-notifications" style={{display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '40vh', flexDirection: 'column'}}>
          <svg width="56" height="56" viewBox="0 0 50 50" style={{marginBottom: 12}} aria-hidden>
            <circle cx="25" cy="25" r="20" stroke="#6366F1" strokeWidth="4" fill="none" strokeLinecap="round" strokeDasharray="31.4 31.4" transform="rotate(-90 25 25)">
              <animateTransform attributeName="transform" type="rotate" from="0 25 25" to="360 25 25" dur="1s" repeatCount="indefinite" />
            </circle>
          </svg>
          <p style={{margin:0, color:'#6b7280'}}>Loading notifications...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="Notification-Main custom-scroll-bar">
      <AnimatePresence mode="wait">
        {/* LIST VIEW */}
        {!selectedNotification && (
          <motion.div
            key="list"
            className="Notis-Tabs"
            initial={{ x: -100, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -100, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            {Object.keys(groupedNotifications).length === 0 ? (
              <div className="no-notifications" style={{display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '40vh', flexDirection: 'column', color:'#6b7280'}}>
                <EnvelopeOpenIcon style={{width:64, height:64, marginBottom:12, color:'#9CA3AF'}} />
                <p style={{margin:0, fontSize:16}}>No notifications yet</p>
              </div>
            ) : (
              Object.keys(groupedNotifications).map((date) => (
                <ul key={date} className="Notis-Tabs-UL">
                  <h2>{date}</h2>
                  {groupedNotifications[date].map((n) => (
                    <li
                      key={n.id}
                      className={`noti-LI-TABr ${
                        n.read_at ? "Read" : ""
                      }`}
                      onClick={() => handleNotificationClick(n)}
                    >
                      <div className="noti-LI-TABr-1">
                        <span>
                          {n.read_at ? (
                            <EnvelopeOpenIcon />
                          ) : (
                            <EnvelopeIcon />
                          )}
                        </span>
                      </div>
                      <div className="noti-LI-TABr-2">
                        <div className="noti-LI-TABr-2-Main">
                          <h5>{n.title}</h5>
                          <p>{n.message}</p>
                          <span>
                            {n.date} <i className="cirlce-icon"></i> {n.time}
                          </span>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              ))
            )}
          </motion.div>
        )}

        {/* READ VIEW */}
        {selectedNotification && (
          <motion.div
            key="read"
            className="Notis-Read"
            initial={{ x: 100, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 100, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="Notis-Read-Top">
              <span className="back-Aroow" onClick={handleBack}>
                <ArrowLeftIcon />
              </span>
              <p>
                {selectedNotification.created_at} <i className="cirlce-icon"></i>{" "}
                {selectedNotification.created_at}
              </p>
            </div>
            <div className="Notis-Read-Main">
              <h5>{selectedNotification.title}</h5>
              <p>{selectedNotification.message}</p>
              {selectedNotification.data && Object.keys(selectedNotification.data).length > 0 && (
                <div className="notification-data">
                  <h6>Additional Data:</h6>
                  <pre>{JSON.stringify(selectedNotification.data, null, 2)}</pre>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Notification;