import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './ChattingApp.css';
import Messaging from './Messaging';
import { XMarkIcon } from '@heroicons/react/24/outline';
import { fetchUserChats } from '../../Pages/CompanyDashboard/Recruitment/ApiService';

import MembImg1 from './Img/memberIcon1.jpg';
import MembImg2 from './Img/memberIcon2.jpg';

const INDICATORS = 7;
const GAP = 50;
const CLOSED_GAP = 6;

const dotColors = [
  'rgba(114, 38, 255, 0.9)',
  '#BFA1FF',
  '#C38BFF',
  '#C574FF',
  '#BB5EFF',
  '#A548FF',
  '#B07DFF',
  '#A366FF',
];

const ChattingApp = () => {
  const [open, setOpen] = useState(false);
  const [showMessaging, setShowMessaging] = useState(false);
  const [selectedSender, setSelectedSender] = useState(null);
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(true);
  const chatRef = useRef(null);

  // Load user chats on component mount
  useEffect(() => {
    const loadChats = async () => {
      try {
        setLoading(true);
        const userChats = await fetchUserChats();
        setChats(userChats || []);
      } catch (error) {
        console.error('Error loading chats:', error);
        setChats([]);
      } finally {
        setLoading(false);
      }
    };

    loadChats();
  }, []);

  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (open && chatRef.current && !chatRef.current.contains(event.target)) {
        setOpen(false);
      }
    };

    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [open]);

  const variants = {
    closed: (i) => ({
      y: -CLOSED_GAP * i,
      opacity: i === 0 ? 0 : 1,
      transition: { type: 'spring', stiffness: 400 },
    }),
    open: (i) => ({
      y: -GAP * (i + 1),
      opacity: 1,
      transition: { type: 'spring', stiffness: 120, delay: 0.03 * i },
    }),
  };

  const badgeVariants = {
    hidden: { opacity: 0, scale: 0.5, transition: { duration: 0.2 } },
    visible: { opacity: 1, scale: 1, transition: { duration: 0.3 } },
  };

  const messagingVariants = {
    hidden: { opacity: 0, scale: 0.8, y: 50 },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
      transition: { type: 'spring', stiffness: 200, damping: 20 },
    },
    exit: { opacity: 0, scale: 0.8, y: 50, transition: { duration: 0.3 } },
  };

  const handleIndicatorClick = (chat, isCloseIcon = false) => {
    if (isCloseIcon) {
      setOpen(false);
    } else if (open) {
      // Transform chat data to match Messaging component expectations per MESSAGING.MD spec
      const sender = {
        id: chat.participants && chat.participants[0]?.id,
        name: chat.name,
        chatId: chat.id,
        img: chat.participants && chat.participants[0]?.profile_image_url || null,
        initials: chat.participants && chat.participants[0] ? (
          chat.participants[0].firstName && chat.participants[0].lastName
            ? `${chat.participants[0].firstName.charAt(0)}${chat.participants[0].lastName.charAt(0)}`.toUpperCase()
            : chat.participants[0].username ? chat.participants[0].username.slice(0, 2).toUpperCase() : 'U'
        ) : 'U',
        staffId: chat.participants && chat.participants[0]?.id,
        unreadCount: chat.unreadCount || 0,
      };
      setSelectedSender(sender);
      setShowMessaging(true);
    }
  };

  // Create display data from chats
  const displayChats = open
    ? [{ name: 'Close', isCloseIcon: true }, ...chats.slice(0, 6)] // Limit to 6 chats + close button
    : chats.slice(0, 7); // Show up to 7 chats when closed

  const totalUnreadMessages = chats.reduce((total, chat) => total + (chat.unreadCount || 0), 0);

  return (
    <div className="ChattingApp">
      {!showMessaging && (
        <div className="Chatt-IndBTns" ref={chatRef} onClick={() => setOpen((p) => !p)}>
          {loading ? (
            <div className="loading-indicator">Loading chats...</div>
          ) : (
            displayChats.map((chat, i) => (
              <motion.div
                key={chat.name || `chat-${i}`}
                className="indicator-wrapper"
                custom={i}
                variants={variants}
                animate={open ? 'open' : 'closed'}
                initial="closed"
                onClick={() => handleIndicatorClick(chat, chat.isCloseIcon)}
              >
                <span
                  className="indicator-dot"
                  style={{ backgroundColor: dotColors[i], position: 'relative' }}
                >
                  {chat.isCloseIcon ? (
                    <div
                      className="Clossing-OOIla"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleIndicatorClick(chat, true);
                      }}
                    >
                      <XMarkIcon className="h-6 w-6" style={{ color: 'white' }} />
                    </div>
                  ) : chat.participants && chat.participants[0]?.profile_image_url ? (
                    <img
                      src={chat.participants[0].profile_image_url}
                      alt={chat.name}
                      className="indicator-avatar"
                      style={{
                        width: '100%',
                        height: '100%',
                        objectFit: 'cover',
                        borderRadius: '50%',
                      }}
                    />
                  ) : (
                    chat.participants && chat.participants[0] ?
                      (chat.participants[0].firstName && chat.participants[0].lastName
                        ? `${chat.participants[0].firstName.charAt(0)}${chat.participants[0].lastName.charAt(0)}`.toUpperCase()
                        : chat.participants[0].username ? chat.participants[0].username.slice(0, 2).toUpperCase() : 'U'
                      ) : 'U'
                  )}
                  {chat.unreadCount > 0 && (open || i === displayChats.length - 1) && (
                    <motion.span
                      className="message-count-badge"
                      variants={badgeVariants}
                      initial="hidden"
                      animate="visible"
                      exit="hidden"
                      key={`badge-${i}-${open}`}
                      style={{
                        originX: 1,
                        originY: 0.5,
                        position: 'absolute',
                        top: -8,
                        right: -8,
                      }}
                    >
                      {i === displayChats.length - 1 && !open
                        ? totalUnreadMessages
                        : chat.unreadCount}
                    </motion.span>
                  )}
                </span>
                <div className="sender-label">{chat.name}</div>
              </motion.div>
            ))
          )}
        </div>
      )}

      <AnimatePresence>
        {showMessaging && (
          <>
           <motion.div
                        key="overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 0.5 }}
                        exit={{ opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        onClick={() => setShowMessaging(false)}
                        style={{
                          position: 'fixed',
                          top: 0,
                          left: 0,
                          width: '100vw',
                          height: '100vh',
                          backgroundColor: 'black',
                          zIndex: 2000,
                        }}
                      />
          <motion.div
            variants={messagingVariants}
            key="messaging-panel"
            initial={{ y: 100, opacity: 0, scale: 0.9 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 100, opacity: 0, scale: 0.9 }}
            transition={{ type: 'spring', stiffness: 200, damping: 20 }}
            className="ppol-Messaging-Section"
          >
            <Messaging
              closeMessaging={() => setShowMessaging(false)}
              sender={selectedSender} // Pass the selected sender
            />
          </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ChattingApp;