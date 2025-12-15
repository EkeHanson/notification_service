import React, { useRef, useState, useEffect } from "react";
import "./Messaging.css";
import {
  MicrophoneIcon,
  PaperAirplaneIcon,
  FaceSmileIcon,
  PaperClipIcon,
  XMarkIcon,
  TrashIcon,
  NoSymbolIcon,
  CheckIcon,
} from "@heroicons/react/24/outline";
import { motion, AnimatePresence } from "framer-motion";
import { PlayIcon, PauseIcon } from "@heroicons/react/24/solid";
import Picker from "@emoji-mart/react";
import data from "@emoji-mart/data";
import FileIcon from "../../assets/Img/./icons/new-document.png";
import chatImg from "../../assets/Img/NochatIcon.png";
import CLearChatImg from "../../assets/Img/clear-chat-img.png";
import {
  fetchConversationMessages,
  sendConversationMessage,
  markMessagesAsRead,
  uploadChatFile,
  fetchChatConversations,
  createChatConversation,
  addConversationParticipant,
  fetchMessageReactions,
  addMessageReaction,
  updateMyPresence,
} from "../../Pages/CompanyDashboard/Recruitment/ApiService";
import { WEBSOCKET_URL } from "../../config";

const formatDisplayDate = (date) => {
  const today = new Date();
  if (
    date.getDate() === today.getDate() &&
    date.getMonth() === today.getMonth() &&
    date.getFullYear() === today.getFullYear()
  ) {
    return "Today";
  }
  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

// Calendar Dropdown Component
const CalendarDropdown = ({ selectedDate, onSelect, onClose }) => {
  const [currentMonth, setCurrentMonth] = useState(selectedDate.getMonth());
  const [currentYear, setCurrentYear] = useState(selectedDate.getFullYear());
  const calendarRef = useRef(null);

  // Get days in month
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
  const firstDayOfMonth = new Date(currentYear, currentMonth, 1).getDay();

  // Generate days array
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);

  // Previous month
  const prevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear(currentYear - 1);
    } else {
      setCurrentMonth(currentMonth - 1);
    }
  };

  // Next month
  const nextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear(currentYear + 1);
    } else {
      setCurrentMonth(currentMonth + 1);
    }
  };

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (calendarRef.current && !calendarRef.current.contains(e.target)) {
        onClose();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  return (
    <div className="OOcalendar-dropdown" ref={calendarRef}>
      <div className="OOcalendar-header">
        <button onClick={prevMonth}>{"<"}</button>
        <h4>
          {new Date(currentYear, currentMonth).toLocaleDateString("en-US", {
            month: "long",
            year: "numeric",
          })}
        </h4>
        <button onClick={nextMonth}>{">"}</button>
      </div>
      <div className="OOcalendar-weekdays">
        {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((day, i) => (
          <div key={i} className="weekday">
            {day}
          </div>
        ))}
      </div>
      <div className="OOcalendar-days">
        {Array(firstDayOfMonth)
          .fill(null)
          .map((_, i) => (
            <div key={`empty-${i}`} className="calendar-day empty"></div>
          ))}
        {days.map((day) => {
          const isSelected =
            day === selectedDate.getDate() &&
            currentMonth === selectedDate.getMonth() &&
            currentYear === selectedDate.getFullYear();
          const isToday =
            day === new Date().getDate() &&
            currentMonth === new Date().getMonth() &&
            currentYear === new Date().getFullYear();
          return (
            <div
              key={day}
              className={`OOcalendar-day ${isSelected ? "selected" : ""} ${
                isToday ? "today" : ""
              }`}
              onClick={() => {
                const newDate = new Date(currentYear, currentMonth, day);
                onSelect(newDate);
                onClose();
              }}
            >
              {day}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Add this outside the component to make it globally available
const checkAutoReplies = () => {
  const allSenders = Object.keys(localStorage)
    .filter((key) => key.startsWith("chatMessages_"))
    .map((key) => key.replace("chatMessages_", ""));

  allSenders.forEach((sender) => {
    const storageKey = `chatMessages_${sender}`;
    const autoReplyKey = `hasAutoReplied_${sender}`;
    const sentMessagesKey = `sentMessages_${sender}`;

    const hasAutoReplied = localStorage.getItem(autoReplyKey) === "true";
    if (hasAutoReplied) return;

    const sentMessages = JSON.parse(
      localStorage.getItem(sentMessagesKey) || "[]"
    );
    const needsAutoReply = sentMessages.some(
      (msg) => Date.now() - msg.timestamp >= 5000
    );

    if (needsAutoReply) {
      // Add auto-reply message
      const messages = JSON.parse(localStorage.getItem(storageKey) || "[]");
      const autoReplyMessage = {
        id: Date.now(),
        text: `Hello, this is ${sender.replace(
          /_/g,
          " "
        )}. I'm currently unavailable but will respond as soon as possible.`,
        type: "text",
        direction: "received",
        timestamp: new Date().toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          hour12: true,
        }),
      };

      messages.push(autoReplyMessage);
      localStorage.setItem(storageKey, JSON.stringify(messages));
      localStorage.setItem(autoReplyKey, "true");
    }
  });
};

// Set up global interval
setInterval(checkAutoReplies, 1000);

const Messaging = ({ closeMessaging, sender, jwtToken, currentUserId, chatId, onSendMessage }) => {

  console.log("sender")
  console.log(sender)
  console.log("sender")
  // Fallback to localStorage if props not provided
  const userFromStorage = JSON.parse(localStorage.getItem("user") || localStorage.getItem("userData") || localStorage.getItem("currentUser") || 'null');
  const effectiveCurrentUserId = currentUserId || sender?.id || userFromStorage?.id;
  const effectiveJwtToken = jwtToken || localStorage.getItem('accessToken') || localStorage.getItem('token') || localStorage.getItem('access_token');
  const effectiveChatId = chatId || sender?.chatId;

  const textareaRef = useRef(null);
  const chatBodyRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordingIntervalRef = useRef(null);

  // Default sender
  const defaultSender = { name: "Sophia Eleto", initials: "SE" };
  const currentSender = sender || defaultSender;

  // Use API-based messaging if chatId is available, otherwise fallback to localStorage
  const useApi = chatId !== undefined;
  const storageKey = `chatMessages_${currentSender.name.replace(/\s+/g, "_")}`;
  const draftKey = `draftMessage_${currentSender.name.replace(/\s+/g, "_")}`;
  const autoReplyKey = `hasAutoReplied_${currentSender.name.replace(
    /\s+/g,
    "_"
  )}`;

  // Initialize messages, draft, and auto-reply state
  const [messages, setMessages] = useState([]);
  const [messageText, setMessageText] = useState(() => {
    const savedDraft = localStorage.getItem(draftKey);
    return savedDraft || "";
  });
  const [hasAutoReplied, setHasAutoReplied] = useState(() => {
    const savedAutoReply = localStorage.getItem(autoReplyKey);
    return savedAutoReply === "true";
  });
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [wordCount, setWordCount] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState("00:00");
  const [recordedBlob, setRecordedBlob] = useState(null);
  const [recordedAudioUrl, setRecordedAudioUrl] = useState(null);
  const [previewDuration, setPreviewDuration] = useState(0);
  const [previewCurrentTime, setPreviewCurrentTime] = useState(0);
  const [previewIsPlaying, setPreviewIsPlaying] = useState(false);
  const [messageStatus, setMessageStatus] = useState({});
  const [showDelete, setShowDelete] = useState(null);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const emojiPickerRef = useRef(null);

  const pendingSendRef = useRef(false);
  const audioRefs = useRef({});
  const playbackStates = useRef({});

  const [attachedFile, setAttachedFile] = useState(null);
  const fileInputRef = useRef(null);

  const [playbackTick, setPlaybackTick] = useState(0);

  const [showCalendar, setShowCalendar] = useState(false);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const calendarToggleRef = useRef(null);
  const [calendarPosition, setCalendarPosition] = useState({ top: 0, left: 0 });
  const calendarButtonRef = useRef(null);

  const justToggledRef = useRef(false);

  const [showDateSpan, setShowDateSpan] = useState(false);

  // Track sent messages for auto-reply
  const [sentMessages, setSentMessages] = useState([]);

  // Message reactions state
  const [messageReactions, setMessageReactions] = useState({});
  const [showReactionPicker, setShowReactionPicker] = useState(null);

  // WebSocket for real-time messaging
  const [socket, setSocket] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  // Load messages when component mounts or sender changes
  useEffect(() => {
    const loadMessages = async () => {
      if (useApi && chatId) {
        try {
          setLoadingMessages(true);
          const response = await fetchConversationMessages(chatId, { limit: 50 });
          const apiMessages = response.results || [];

          // Transform API messages to component format
          const transformedMessages = apiMessages.map((msg) => ({
            id: msg.id,
            text: msg.content,
            type: msg.message_type || "text",
            direction: msg.sender_id === currentUserId ? "sent" : "received",
            timestamp: new Date(msg.created_at).toLocaleTimeString("en-US", {
              hour: "2-digit",
              minute: "2-digit",
              hour12: true,
            }),
            read: true, // API messages are already delivered
            file_url: msg.file_url,
            file_name: msg.file_name,
            file_size: msg.file_size,
            reply_to: msg.reply_to,
            reactions: msg.reactions || [],
          }));

          setMessages(transformedMessages);
        } catch (error) {
          console.error('Error loading messages:', error);
          // Fallback to localStorage
          const savedMessages = localStorage.getItem(storageKey);
          setMessages(savedMessages ? JSON.parse(savedMessages) : []);
        } finally {
          setLoadingMessages(false);
        }
      } else {
        // Fallback to localStorage
        const savedMessages = localStorage.getItem(storageKey);
        setMessages(savedMessages ? JSON.parse(savedMessages) : []);
      }
    };

    loadMessages();
  }, [chatId, currentUserId, useApi]);

  // WebSocket connection for real-time messaging
   useEffect(() => {
     console.log('🔄 [DEBUG] WebSocket useEffect triggered', {
       useApi,
       chatId,
       currentUserId,
       sender: currentSender,
       jwtToken: jwtToken ? 'present' : 'missing'
     });

     if (useApi && chatId) {
       const token = jwtToken || localStorage.getItem('accessToken');
       const tenantId = localStorage.getItem('tenantId') || localStorage.getItem('tenantUniqueId') || 'default-tenant';

       console.log('🚀 [DEBUG] WebSocket connection attempt:', {
         token: token ? 'present' : 'missing',
         tenantId,
         chatId: chatId,
         WEBSOCKET_URL,
         currentUserId,
         localStorageKeys: Object.keys(localStorage).filter(key => key.includes('token') || key.includes('tenant'))
       });

       if (token) {
         // Use native WebSocket with JWT in URL query parameter as per backend spec

        // Use /ws/chat/{tenantId}/ for chat as per backend documentation
        const wsUrl = `${WEBSOCKET_URL}/ws/chat/${tenantId}/?token=${token}`;
        console.log('🔗 [DEBUG] Constructed WebSocket URL:', wsUrl.replace(token, '[REDACTED]'));
        console.log('📡 [DEBUG] Attempting to create WebSocket connection...');
        const newSocket = new WebSocket(wsUrl);

         newSocket.onopen = () => {
           console.log('✅ [DEBUG] WebSocket connection OPENED successfully');
           setIsConnected(true);

           // Join conversation after connection (auth is in URL)
           const joinMessage = {
             type: 'join_conversation',
             conversation_id: chatId
           };
           newSocket.send(JSON.stringify(joinMessage));
           console.log('📤 [DEBUG] Sent join_conversation message:', joinMessage);

           // Update presence
           updateMyPresence({ status: 'online', current_conversation: chatId, user_id: currentUserId });
         };

         newSocket.onclose = (event) => {
           console.log('❌ [DEBUG] WebSocket connection CLOSED:', {
             code: event.code,
             reason: event.reason,
             wasClean: event.wasClean
           });
           setIsConnected(false);
         };

         newSocket.onmessage = (event) => {
           try {
             const data = JSON.parse(event.data);
             console.log('📨 [DEBUG] Received WebSocket message:', data);
             handleWebSocketMessage(data);
           } catch (error) {
             console.error('❌ [DEBUG] Error parsing WebSocket message:', error, 'Raw data:', event.data);
           }
         };

         newSocket.onerror = (error) => {
           console.error('❌ [DEBUG] WebSocket ERROR:', error);
         };

         setSocket(newSocket);

         return () => {
           console.log('🧹 [DEBUG] Cleaning up WebSocket connection');
           if (newSocket.readyState === WebSocket.OPEN) {
             newSocket.close();
           }
         };
       } else {
         console.log('❌ [DEBUG] No access token found, cannot connect to WebSocket');
         console.log('🔍 [DEBUG] Available localStorage keys:', Object.keys(localStorage));
       }
     } else {
       console.log('⏭️ [DEBUG] WebSocket not initialized:', { useApi, chatId, currentUserId });
     }
   }, [chatId, currentUserId, useApi, jwtToken]);

  // Handle WebSocket messages according to MESSAGING.MD specification
  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'connection_established':
        console.log('WebSocket connection established:', data);
        // Store user and tenant info from server if provided
        if (data.user_id && data.tenant_id) {
          localStorage.setItem('chatUserId', data.user_id);
          localStorage.setItem('chatTenantId', data.tenant_id);
        }
        break;

      case 'new_message':
        console.log('Received new_message via WebSocket:', data);
        // Check if this message belongs to the current conversation
        const messageConversation = data.message?.conversation || data.conversation;
        const currentConversation = chatId;
        console.log('Conversation comparison:', {
          messageConversation,
          currentConversation,
          messageData: data.message,
          fullData: data
        });

        // For now, accept all messages and let the UI filter them
        // TODO: Add proper conversation filtering once backend format is confirmed
        if (data.message) {
          console.log('Processing message');
          const newMessage = {
            id: data.message.id,
            text: data.message.content,
            type: data.message.message_type || 'text',
            direction: data.message.sender_id === currentUserId ? "sent" : "received",
            timestamp: new Date(data.message.created_at).toLocaleTimeString("en-US", {
              hour: "2-digit",
              minute: "2-digit",
              hour12: true,
            }),
            created_at: data.message.created_at,
            read: true,
            file_url: data.message.file_url,
            file_name: data.message.file_name,
            file_size: data.message.file_size,
            reply_to: data.message.reply_to,
            reactions: data.message.reactions || [],
          };
          console.log('New message object:', newMessage);

          // Only add if it's not from the current user (to avoid duplicates)
          if (data.message.sender_id !== currentUserId) {
            console.log('Adding received message to state');
            setMessages(prev => {
              // Prevent duplicate messages
              const isDuplicate = prev.some(m => m.id === newMessage.id);
              console.log('Is duplicate message?', isDuplicate);
              if (!isDuplicate) {
                return [...prev, newMessage];
              }
              return prev;
            });
          } else {
            console.log('Skipping own message (already added locally)');
          }

          // Mark messages as read
          if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
              type: 'mark_read',
              conversation_id: chatId
            }));
          }
        }
        break;

      case 'message_updated':
        // Handle message edits per MESSAGING.MD spec
        if (data.message) {
          setMessages(prev => prev.map(msg =>
            msg.id === data.message.id ? {
              ...msg,
              text: data.message.content,
              edited_at: data.message.edited_at,
              type: data.message.message_type || msg.type
            } : msg
          ));
        }
        break;

      case 'message_deleted':
        // Handle message deletion per MESSAGING.MD spec
        if (data.message_id) {
          setMessages(prev => prev.filter(msg => msg.id !== data.message_id));
        }
        break;

      case 'reaction_added':
        // Handle emoji reactions per MESSAGING.MD spec
        if (data.reaction) {
          setMessages(prev => prev.map(msg =>
            msg.id === data.reaction.message_id ? {
              ...msg,
              reactions: [...(msg.reactions || []), {
                id: data.reaction.id,
                emoji: data.reaction.emoji,
                user_id: data.reaction.user_id,
                created_at: data.reaction.created_at
              }]
            } : msg
          ));
        }
        break;

      case 'reaction_removed':
        // Handle reaction removal per MESSAGING.MD spec
        if (data.reaction) {
          setMessages(prev => prev.map(msg =>
            msg.id === data.reaction.message_id ? {
              ...msg,
              reactions: (msg.reactions || []).filter(r => r.id !== data.reaction.id)
            } : msg
          ));
        }
        break;

      case 'typing_indicator':
        // Show typing indicator when other user is typing
        if (data.user_id !== currentUserId && data.is_typing !== undefined) {
          setIsTyping(data.is_typing);
        }
        break;

      case 'user_status_change':
        // Handle online/offline presence updates
        console.log('User status changed:', data);
        break;

      default:
        console.log('Unhandled WebSocket message type:', data.type, data);
    }
  };

  // Initialize textarea with saved draft
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.value = messageText;
      handleInput(); // Update word count and textarea height
    }
  }, [messageText]);

  // Save messages and draft to localStorage when closing
  const handleCloseMessaging = () => {
    // Only save to localStorage if not using API
    if (!useApi) {
      localStorage.setItem(storageKey, JSON.stringify(messages));
    }
    localStorage.setItem(draftKey, messageText);
    localStorage.setItem(autoReplyKey, hasAutoReplied.toString());
    closeMessaging();
  };

  // Clear all chats
  const handleClearChats = () => {
    // Only clear localStorage if not using API
    if (!useApi) {
      localStorage.removeItem(
        `sentMessages_${currentSender.name.replace(/\s+/g, "_")}`
      );
      localStorage.removeItem(
        `hasAutoReplied_${currentSender.name.replace(/\s+/g, "_")}`
      );
      // Revoke all audio and file URLs
      messages.forEach((msg) => {
        if (msg.audioUrl) URL.revokeObjectURL(msg.audioUrl);
        if (msg.previewUrl) URL.revokeObjectURL(msg.previewUrl);
      });
      if (recordedAudioUrl) URL.revokeObjectURL(recordedAudioUrl);

      // Clear localStorage
      localStorage.removeItem(storageKey);
      localStorage.removeItem(draftKey);
      localStorage.removeItem(autoReplyKey);
    }

    // Reset state
    setMessages([]);
    setMessageText("");
    setSentMessages([]);
    setHasAutoReplied(false);
    setMessageStatus({});
    setRecordedBlob(null);
    setRecordedAudioUrl(null);
    setPreviewDuration(0);
    setPreviewCurrentTime(0);
    setPreviewIsPlaying(false);
    setAttachedFile(null);
    setShowDelete(null);
    setShowClearConfirm(false);
    audioRefs.current = {};
    playbackStates.current = {};

    if (textareaRef.current) {
      textareaRef.current.value = "";
      textareaRef.current.style.height = "auto";
      setWordCount(0);
    }
    // Remove No-scroll class on confirm
    if (chatBodyRef.current) {
      chatBodyRef.current.classList.remove("No-scroll");
    }
  };

  // Handle Clear Chat button click
  const handleClearChatClick = () => {
    if (chatBodyRef.current) {
      chatBodyRef.current.classList.add("No-scroll");
    }
    setShowClearConfirm(true);
  };

  // Handle Cancel button click
  const handleCancelClear = () => {
    if (chatBodyRef.current) {
      chatBodyRef.current.classList.remove("No-scroll");
    }
    setShowClearConfirm(false);
  };

  useEffect(() => {
    const chatEl = chatBodyRef.current;
    if (!chatEl) return;

    const handleScroll = () => {
      if (chatEl.scrollTop > 50) {
        setShowDateSpan(true);
      } else {
        setShowDateSpan(false);
      }
    };

    chatEl.addEventListener("scroll", handleScroll);
    return () => chatEl.removeEventListener("scroll", handleScroll);
  }, []);

  // Check for messages that need auto-reply
  useEffect(() => {
    const checkAutoReply = () => {
      if (hasAutoReplied) return; // Skip if auto-reply has already been sent

      const now = Date.now();
      const fiveSeconds = 5 * 1000; // 5 seconds in milliseconds

      const needsAutoReply = sentMessages.some(
        (msg) => now - msg.timestamp >= fiveSeconds
      );

      if (needsAutoReply) {
        setHasAutoReplied(true);
        localStorage.setItem(autoReplyKey, "true");

        // Send auto-reply
        setIsTyping(true);
        setTimeout(() => {
          const autoReplyMessage = {
            id: Date.now(),
            text: `Hello, this is ${currentSender.name}. I'm currently unavailable but will respond as soon as possible.`,
            type: "text",
            direction: "received",
            timestamp: getTimestamp(),
          };

          setMessages((prev) => {
            const newMessages = [...prev, autoReplyMessage];
            localStorage.setItem(storageKey, JSON.stringify(newMessages));
            return newMessages;
          });
          setIsTyping(false);
        }, 2000);
      }
    };

    const interval = setInterval(checkAutoReply, 1000); // Check every second
    return () => clearInterval(interval);
  }, [sentMessages, currentSender.name, hasAutoReplied]);

  function handleFileUpload(file) {
    const isImage = file.type.startsWith("image/");
    const id = Date.now();
    const newMsg = {
      id,
      type: "file",
      fileName: file.name,
      fileSize: file.size,
      previewUrl: isImage ? URL.createObjectURL(file) : null,
      timestamp: getTimestamp(),
      direction: "sent",
    };

    setMessages((prev) => {
      const newMessages = [...prev, newMsg];
      localStorage.setItem(storageKey, JSON.stringify(newMessages));
      return newMessages;
    });
    setMessageStatus((p) => ({ ...p, [id]: "sent" }));
    setSentMessages((prev) => [...prev, { id, timestamp: Date.now() }]);

    setTimeout(
      () => setMessageStatus((p) => ({ ...p, [id]: "delivered" })),
      2000
    );
  }

  useEffect(() => {
    return () => {
      messages.forEach((msg) => {
        if (msg.previewUrl) URL.revokeObjectURL(msg.previewUrl);
      });
    };
  }, []);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setAttachedFile(file);

      // Upload file via API per MESSAGING.MD spec
      const uploadFileToAPI = async () => {
        try {
          const uploadedFile = await uploadChatFile(file);
          
          const id = Date.now();
          const fileMsg = {
            id,
            type: "file",
            fileName: uploadedFile.file_name,
            fileSize: uploadedFile.file_size,
            previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
            direction: "sent",
            timestamp: getTimestamp(),
            file_url: uploadedFile.file_url,
          };

          // Send file message via WebSocket
          if (useApi && chatId && socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
              type: 'send_message',
              conversation_id: chatId,
              message_type: 'file',
              content: `Shared a file: ${uploadedFile.file_name}`,
              file_url: uploadedFile.file_url,
              file_name: uploadedFile.file_name,
              file_size: uploadedFile.file_size
            }));
          } else if (useApi && chatId) {
            // Fallback to API
            await sendConversationMessage(chatId, {
              message_type: 'file',
              content: `Shared a file: ${uploadedFile.file_name}`,
              file_url: uploadedFile.file_url,
              file_name: uploadedFile.file_name,
              file_size: uploadedFile.file_size
            });
          }

          setMessages((prev) => [...prev, fileMsg]);
          setMessageStatus((p) => ({ ...p, [id]: "sent" }));
          setSentMessages((prev) => [...prev, { id, timestamp: Date.now() }]);

          setTimeout(
            () => setMessageStatus((p) => ({ ...p, [id]: "delivered" })),
            2000
          );
        } catch (error) {
          console.error('Error uploading file:', error);
          // Fallback to localStorage
          const id = Date.now();
          const isImage = file.type.startsWith("image/");
          const previewUrl = isImage ? URL.createObjectURL(file) : null;

          const fileMsg = {
            id,
            type: "file",
            fileName: file.name,
            fileSize: file.size,
            previewUrl,
            direction: "sent",
            timestamp: getTimestamp(),
          };

          setMessages((prev) => {
            const newMessages = [...prev, fileMsg];
            localStorage.setItem(storageKey, JSON.stringify(newMessages));
            return newMessages;
          });
          setMessageStatus((p) => ({ ...p, [id]: "sent" }));
          setSentMessages((prev) => [...prev, { id, timestamp: Date.now() }]);

          setTimeout(
            () => setMessageStatus((p) => ({ ...p, [id]: "delivered" })),
            2000
          );
        }
      };

      uploadFileToAPI();
    }
  };

  const addEmoji = (emoji) => {
    const cursorPosition = textareaRef.current.selectionStart;
    const text = messageText;
    const updatedText =
      text.slice(0, cursorPosition) + emoji.native + text.slice(cursorPosition);
    setMessageText(updatedText);
    localStorage.setItem(draftKey, updatedText); // Save draft

    // Update textarea manually
    if (textareaRef.current) {
      textareaRef.current.value = updatedText;
      textareaRef.current.focus();
      textareaRef.current.selectionEnd = cursorPosition + emoji.native.length;
      handleInput();
    }
  };

  // Add reaction to message per MESSAGING.MD spec
  const addReactionToMessage = async (messageId, emoji) => {
    try {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
          type: 'add_reaction',
          message_id: messageId,
          emoji: emoji
        }));
      } else if (useApi) {
        // Fallback to API
        await addMessageReaction(messageId, { emoji });
      }
      setShowReactionPicker(null);
    } catch (error) {
      console.error('Error adding reaction:', error);
    }
  };

  // Remove reaction from message per MESSAGING.MD spec
  const removeReactionFromMessage = async (messageId, emoji) => {
    try {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
          type: 'remove_reaction',
          message_id: messageId,
          emoji: emoji
        }));
      }
      setShowReactionPicker(null);
    } catch (error) {
      console.error('Error removing reaction:', error);
    }
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        emojiPickerRef.current &&
        !emojiPickerRef.current.contains(event.target) &&
        textareaRef.current &&
        !textareaRef.current.contains(event.target)
      ) {
        setShowEmojiPicker(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  /* auto-scroll ------------------------------------------------------ */
  useEffect(() => {
    if (!chatBodyRef.current) return;

    const chatEl = chatBodyRef.current;
    const isNearBottom =
      chatEl.scrollHeight - chatEl.scrollTop - chatEl.clientHeight < 80;

    if (isNearBottom) {
      chatEl.scrollTop = chatEl.scrollHeight;
    }
  }, [messages, isTyping]);

  /* ------------------------------------------------------------------ */
  /*                   UTILS (decode, timestamp, format)                */
  /* ------------------------------------------------------------------ */
  const decodeBlobDuration = async (blob) => {
    try {
      const arrayBuffer = await blob.arrayBuffer();
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const decoded = await ctx.decodeAudioData(arrayBuffer);
      return decoded.duration;
    } catch (e) {
      console.error("decode failed", e);
      return 0;
    }
  };

  const getTimestamp = () =>
    new Date().toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });

  const formatTime = (sec) => {
    if (!sec || !isFinite(sec)) return "00:00";
    const m = String(Math.floor(sec / 60)).padStart(2, "0");
    const s = String(Math.round(sec % 60)).padStart(2, "0");
    return `${m}:${s}`;
  };

  /* ------------------------------------------------------------------ */
  /*                        RECORD / PREVIEW LOGIC                      */
  /* ------------------------------------------------------------------ */
  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      clearInterval(recordingIntervalRef.current);
      setRecordingTime("00:00");
      return;
    }

    if (!navigator.mediaDevices || !MediaRecorder) {
      console.error("MediaRecorder not supported");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);

      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/webm" });
        const url = URL.createObjectURL(blob);
        setRecordedBlob(blob);
        setRecordedAudioUrl(url);

        const dur = await decodeBlobDuration(blob);
        setPreviewDuration(dur);

        stream.getTracks().forEach((t) => t.stop());

        if (pendingSendRef.current) {
          addAudioMessage(url, dur);
          resetPreviewState();
          pendingSendRef.current = false;
        }
      };

      recorder.start();
      setIsRecording(true);
      setRecordingTime("00:00");
      const started = Date.now();
      recordingIntervalRef.current = setInterval(() => {
        const elapsed = Date.now() - started;
        const m = String(Math.floor(elapsed / 60000)).padStart(2, "0");
        const s = String(Math.floor((elapsed % 60000) / 1000)).padStart(2, "0");
        setRecordingTime(`${m}:${s}`);
      }, 1000);
    } catch (e) {
      console.error("mic error", e);
      setIsRecording(false);
    }
  };

  const resetPreviewState = () => {
    setRecordedBlob(null);
    setRecordedAudioUrl(null);
    setPreviewDuration(0);
    setPreviewCurrentTime(0);
    setPreviewIsPlaying(false);
  };

  /* ------------------------------------------------------------------ */
  /*                         SENDING MESSAGES                           */
  /* ------------------------------------------------------------------ */
  const sendMessage = async () => {
    if (isRecording) {
      pendingSendRef.current = true;
      toggleRecording();
      return;
    }

    if (recordedAudioUrl) {
      addAudioMessage(recordedAudioUrl, previewDuration);
      resetPreviewState();
      return;
    }

    if (!messageText.trim()) return;

    const id = Date.now();
    const newMessage = {
      id,
      type: "text",
      direction: "sent",
      text: messageText.trim(),
      timestamp: getTimestamp(),
      read: false, // Mark as unread initially
    };

    // Try to send via API first
    if (useApi && chatId) {
      try {
        const messageData = {
          message_type: "text",
          content: messageText.trim(),
        };

        // Send via WebSocket if connected, otherwise via API
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({
            type: 'send_message',
            conversation_id: chatId,
            content: messageText.trim(),
            message_type: 'text'
          }));
          console.log('Message sent via WebSocket');
        } else {
          // Fallback to HTTP API
          const response = await sendConversationMessage(chatId, messageData);
          console.log('Message sent via API:', response);
        }

        // Add message to local state immediately
        setMessages((prev) => [...prev, newMessage]);
        
        // Notify parent component about the sent message
        if (onSendMessage) {
          onSendMessage(chatId, messageText.trim());
        }
        
        // Stop typing indicator
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({
            type: 'stop_typing',
            conversation_id: chatId
          }));
        }
      } catch (error) {
        console.error('Error sending message via API:', error);
        // Fallback to localStorage
        setMessages((prev) => {
          const newMessages = [...prev, newMessage];
          localStorage.setItem(storageKey, JSON.stringify(newMessages));
          return newMessages;
        });
      }
    } else if (!useApi) {
      // Fallback to localStorage
      setMessages((prev) => {
        const newMessages = [...prev, newMessage];
        localStorage.setItem(storageKey, JSON.stringify(newMessages));
        return newMessages;
      });
    }

    // Update sent messages for auto-reply tracking
    const updatedSentMessages = [
      ...sentMessages,
      { id, timestamp: Date.now() },
    ];
    setSentMessages(updatedSentMessages);

    // Store in localStorage for global access
    localStorage.setItem(
      `sentMessages_${currentSender.name.replace(/\s+/g, "_")}`,
      JSON.stringify(updatedSentMessages)
    );

    setMessageStatus((prev) => ({ ...prev, [id]: "sent" }));
    localStorage.setItem(draftKey, ""); // Clear draft after sending

    setTimeout(
      () => setMessageStatus((prev) => ({ ...prev, [id]: "delivered" })),
      2000
    );

    setMessageText("");
    setWordCount(0);
    if (textareaRef.current) {
      textareaRef.current.value = "";
      textareaRef.current.style.height = "auto";
    }
  };
  const addAudioMessage = (audioUrl, duration) => {
    const id = Date.now();
    setMessages((p) => {
      const newMessages = [
        ...p,
        {
          id,
          type: "audio",
          direction: "sent",
          audioUrl,
          duration,
          timestamp: getTimestamp(),
        },
      ];
      localStorage.setItem(storageKey, JSON.stringify(newMessages));
      return newMessages;
    });
    setMessageStatus((p) => ({ ...p, [id]: "sent" }));
    setSentMessages((prev) => [...prev, { id, timestamp: Date.now() }]);

    playbackStates.current[id] = {
      isPlaying: false,
      currentTime: 0,
      duration: duration || 0,
    };
    setTimeout(
      () => setMessageStatus((p) => ({ ...p, [id]: "delivered" })),
      2000
    );
  };

  /* ------------------------------------------------------------------ */
  /*                            PLAYBACK                                */
  /* ------------------------------------------------------------------ */
  const toggleAudioPlayback = (id) => {
    const audio = audioRefs.current[id];
    const st = playbackStates.current[id];
    if (!audio || !st) return;

    if (st.isPlaying) {
      audio.pause();
      playbackStates.current[id] = { ...st, isPlaying: false };
    } else {
      /* pause any other playing note */
      Object.keys(audioRefs.current).forEach((k) => {
        if (k !== id.toString() && playbackStates.current[k]?.isPlaying) {
          audioRefs.current[k].pause();
          playbackStates.current[k] = {
            ...playbackStates.current[k],
            isPlaying: false,
            currentTime: 0,
          };
        }
      });
      audio.currentTime = 0;
      playbackStates.current[id] = { ...st, isPlaying: true, currentTime: 0 };
      audio.play().catch(console.error);
    }
    setMessages((p) => [...p]); // force re-render
  };

  const togglePreviewPlayback = () => {
    const audio = audioRefs.current.preview;
    if (!audio) return;
    if (previewIsPlaying) {
      audio.pause();
      setPreviewIsPlaying(false);
    } else {
      audio.currentTime = 0;
      setPreviewCurrentTime(0);
      audio.play().catch(console.error);
      setPreviewIsPlaying(true);
    }
  };

  /* ------------------------------------------------------------------ */
  /*                        DELETE MESSAGE                              */
  /* ------------------------------------------------------------------ */
  const deleteMessage = (id) => {
    if (audioRefs.current[id] && playbackStates.current[id]?.isPlaying) {
      audioRefs.current[id].pause();
      playbackStates.current[id].isPlaying = false;
    }
    const msg = messages.find((m) => m.id === id);
    if (msg?.type === "audio") URL.revokeObjectURL(msg.audioUrl);

    setMessages((p) => {
      const newMessages = p.filter((m) => m.id !== id);
      localStorage.setItem(storageKey, JSON.stringify(newMessages));
      return newMessages;
    });
    setMessageStatus((p) => {
      const n = { ...p };
      delete n[id];
      return n;
    });
    setSentMessages((prev) => prev.filter((m) => m.id !== id));
    delete audioRefs.current[id];
    delete playbackStates.current[id];
    setShowDelete(null);
  };

  /* ------------------------------------------------------------------ */
  /*                    INPUT (textarea) HANDLERS                       */
  /* ------------------------------------------------------------------ */
  const handleInput = () => {
    const t = textareaRef.current;
    if (!t) return;
    t.style.height = "auto";
    t.style.height = `${Math.min(t.scrollHeight, 150)}px`;
    const txt = t.value.trim();
    const words = txt ? txt.split(/\s+/).length : 0;
    if (words <= 100) {
      setWordCount(words);
      setMessageText(t.value);
      localStorage.setItem(draftKey, t.value); // Save draft on input

      // Send typing indicator per MESSAGING.MD spec
      if (socket && socket.readyState === WebSocket.OPEN && chatId) {
        if (txt.length > 0) {
          socket.send(JSON.stringify({
            type: 'start_typing',
            conversation_id: chatId
          }));
        } else {
          socket.send(JSON.stringify({
            type: 'stop_typing',
            conversation_id: chatId
          }));
        }
      }
    } else {
      const valid = txt.split(/\s+/).slice(0, 100).join(" ");
      t.value = valid;
      setWordCount(100);
      setMessageText(valid);
      localStorage.setItem(draftKey, valid); // Save draft on input
    }
  };

  const handleKeyDown = (e) => {
    if (wordCount >= 100 && !["Backspace", "Delete"].includes(e.key))
      e.preventDefault();
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  /* ------------------------------------------------------------------ */
  /*                        ANIMATION VARIANTS                          */
  /* ------------------------------------------------------------------ */
  const msgVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
    exit: { opacity: 0, y: 20, transition: { duration: 0.3 } },
  };

  const confirmVariants = {
    hidden: { opacity: 0, scale: 1 },
    visible: { opacity: 1, scale: 1, transition: { duration: 0.3 } },
    exit: { opacity: 0, scale: 1, transition: { duration: 0.3 } },
  };

  /* ------------------------------------------------------------------ */
  /*                              RENDER                                */
  /* ------------------------------------------------------------------ */
  return (
    <div className="ppol-Messaging-Apss Simp-Boxshadow">
      {/* ---------- HEADER ---------- */}
      <div className="MMApss-Top">
        <div className="MMApss-Top-1">
          <div className="MMApss-Top-10">
            {currentSender.img || currentSender.avatar ? (
              <img
                src={currentSender.img || currentSender.avatar}
                alt={currentSender.name}
              />
            ) : (
              <span>{currentSender.initials}</span>
            )}
          </div>
          <div className="MMApss-Top-11">
            <h5>{currentSender.name}</h5>
            <p>
              {currentSender.staffId
                ? `Staff ID: ${currentSender.staffId}`
                : "Online"}
            </p>
          </div>
        </div>
        <div className="MMApss-Top-2">
          <span
            onClick={handleClearChatClick}
            className="cursor-pointer"
            title="Clear chat"
          >
            <NoSymbolIcon className="h-6 w-6" />
          </span>
          <span
            onClick={handleCloseMessaging}
            className="cursor-pointer"
            title="Close chat"
          >
            <XMarkIcon />
          </span>
        </div>
      </div>
      <AnimatePresence>
        {showClearConfirm && (
          <motion.div
            className="clear-confirm-section"
            variants={confirmVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <div className="Confom-Main">
              <img src={CLearChatImg} />
              <p>Do you want to clear all your chats permanently?</p>
              <div className="clear-confirm-buttons">
                <button className="clear-confirm-ok" onClick={handleClearChats}>
                  Yes
                </button>
                <button
                  className="clear-confirm-cancel"
                  onClick={handleCancelClear}
                >
                  No
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      {/* ---------- BODY ---------- */}
      <div className="MMApss-Body custom-scroll-bar" ref={chatBodyRef}>
        <div className="Datgg-Puks-Cha">
          <AnimatePresence>
            {showDateSpan && (
              <motion.span
                ref={calendarToggleRef}
                className="today-link"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                onClick={(e) => {
                  justToggledRef.current = true;
                  setTimeout(() => (justToggledRef.current = false), 150);

                  if (showCalendar) {
                    setShowCalendar(false);
                  } else {
                    const r = e.target.getBoundingClientRect();
                    setCalendarPosition({
                      top: r.bottom + window.scrollY,
                      left: r.left + window.scrollX,
                    });
                    setShowCalendar(true);
                  }
                }}
              >
                {formatDisplayDate(selectedDate)}
              </motion.span>
            )}
          </AnimatePresence>

          {showCalendar && (
            <div className="OK-CChtt-Callenad">
              <CalendarDropdown
                selectedDate={selectedDate}
                onSelect={(date) => {
                  setSelectedDate(date);
                  setShowCalendar(false);
                }}
                onClose={() => setShowCalendar(false)}
              />
            </div>
          )}
        </div>

        {loadingMessages ? (
          <div className="no-messages-container">
            <div className="no-messages-content">
              <p>Loading messages...</p>
            </div>
          </div>
        ) : messages.length === 0 && !isTyping && !showClearConfirm && (
          <div className="no-messages-container">
            <div className="no-messages-content">
              <img src={chatImg} />
              <h3>No messages yet!</h3>
              <p>Start a conversation by sending a message</p>
            </div>
          </div>
        )}

        <AnimatePresence>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              className={`Chatt-Box ${
                msg.direction === "received"
                  ? "recivvv-Chatt-Box"
                  : "SeNNdi-Chatt-Box"
              }`}
              variants={msgVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              onMouseEnter={() =>
                msg.direction === "sent" && setShowDelete(msg.id)
              }
              onMouseLeave={() => setShowDelete(null)}
            >
              {/* ---------- AUDIO ---------- */}
              {msg.type === "audio" && (
                <div className="voice-preview">
                  <div className="voice-playback">
                    <span
                      onClick={() => toggleAudioPlayback(msg.id)}
                      className="fff-Controll cursor-pointer"
                    >
                      {playbackStates.current[msg.id]?.isPlaying ? (
                        <PauseIcon className="h-5 w-5 text-blue-600" />
                      ) : (
                        <PlayIcon className="h-5 w-5 text-blue-600" />
                      )}
                    </span>

                    <div className="voice-waveform">
                      {Array.from({ length: 20 }).map((_, i) => (
                        <div
                          key={i}
                          className={`voice-wave-bar ${
                            msg.duration > 0 &&
                            i <
                              Math.floor(
                                (playbackStates.current[msg.id]?.currentTime /
                                  msg.duration) *
                                  20
                              )
                              ? "active"
                              : ""
                          }`}
                        />
                      ))}
                    </div>

                    {msg.direction === "sent" && showDelete === msg.id && (
                      <span
                        className="delete-message cursor-pointer ml-2"
                        onClick={() => deleteMessage(msg.id)}
                        aria-label="Delete message"
                      >
                        <XMarkIcon className="h-4 w-4 text-red-600" />
                      </span>
                    )}
                  </div>

                  <div className="ggyh-aolks">
                    <span className="voice-time">
                      {playbackStates.current[msg.id]?.isPlaying
                        ? formatTime(
                            playbackStates.current[msg.id]?.currentTime
                          )
                        : formatTime(msg.duration)}
                    </span>

                    {/* -------- timestamp / status ---------- */}
                    <span className="timestamp-container">
                      {msg.timestamp}
                      {msg.direction !== "received" && (
                        <span className="status-icons">
                          {messageStatus[msg.id] === "sent" ? (
                            <CheckIcon className="h-4 w-4 text-gray-500" />
                          ) : (
                            <span className="double-check">
                              <CheckIcon className="h-4 w-4 text-blue-500" />
                              <CheckIcon className="h-4 w-4 text-blue-500" />
                            </span>
                          )}
                        </span>
                      )}
                    </span>
                  </div>

                  <audio
                    ref={(el) => (audioRefs.current[msg.id] = el)}
                    src={msg.audioUrl}
                    hidden
                    preload="metadata"
                    onTimeUpdate={() => {
                      if (audioRefs.current[msg.id]) {
                        playbackStates.current[msg.id] = {
                          ...playbackStates.current[msg.id],
                          currentTime: audioRefs.current[msg.id].currentTime,
                        };
                        setPlaybackTick((tick) => tick + 1);
                      }
                    }}
                    onLoadedMetadata={() => {
                      if (audioRefs.current[msg.id] && !msg.duration) {
                        playbackStates.current[msg.id].duration =
                          audioRefs.current[msg.id].duration;
                        setMessages((p) =>
                          p.map((m) =>
                            m.id === msg.id
                              ? {
                                  ...m,
                                  duration: audioRefs.current[msg.id].duration,
                                }
                              : m
                          )
                        );
                      }
                    }}
                    onEnded={() => {
                      playbackStates.current[msg.id] = {
                        ...playbackStates.current[msg.id],
                        isPlaying: false,
                        currentTime: 0,
                      };
                      setMessages((p) => [...p]);

                      // auto-play next audio note
                      const nextIdx =
                        messages.findIndex((m) => m.id === msg.id) + 1;
                      if (
                        nextIdx < messages.length &&
                        messages[nextIdx].type === "audio"
                      ) {
                        const nextId = messages[nextIdx].id;
                        const nxtA = audioRefs.current[nextId];
                        if (nxtA) {
                          playbackStates.current[nextId] = {
                            ...playbackStates.current[nextId],
                            isPlaying: true,
                            currentTime: 0,
                          };
                          nxtA.currentTime = 0;
                          nxtA.play().catch(console.error);
                          setMessages((p) => [...p]);
                        }
                      }
                    }}
                  />
                </div>
              )}

              {/* ---------- FILE ---------- */}
              {msg.type === "file" && (
                <div className="file-message">
                  <div className="file-icon-name">
                    <img
                      src={msg.previewUrl || FileIcon}
                      alt={msg.fileName}
                      className="file-preview-image"
                    />
                    <span>{msg.fileName}</span>

                    {msg.direction === "sent" && showDelete === msg.id && (
                      <span
                        className="delete-message cursor-pointer ml-2"
                        onClick={() => deleteMessage(msg.id)}
                        aria-label="Delete message"
                      >
                        <XMarkIcon className="h-4 w-4 text-red-600" />
                      </span>
                    )}
                  </div>

                  <div className="file-meta">
                    <span>{(msg.fileSize / 1024).toFixed(1)} KB</span>
                    <span className="timestamp-container">
                      {msg.timestamp}
                      {msg.direction === "sent" && (
                        <span className="status-icons">
                          {messageStatus[msg.id] === "sent" ? (
                            <CheckIcon className="h-4 w-4 text-gray-500" />
                          ) : (
                            <span className="double-check">
                              <CheckIcon className="h-4 w-4 text-blue-500" />
                              <CheckIcon className="h-4 w-4 text-blue-500" />
                            </span>
                          )}
                        </span>
                      )}
                    </span>
                  </div>
                </div>
              )}

              {/* ---------- TEXT ---------- */}
              {msg.type === "text" && (
                <>
                  <p>{msg.text}</p>
                  <span className="timestamp-container">
                    {msg.timestamp}
                    {msg.direction === "sent" && (
                      <span className="status-icons">
                        {messageStatus[msg.id] === "sent" ? (
                          <CheckIcon className="h-4 w-4 text-gray-500" />
                        ) : (
                          <span className="double-check">
                            <CheckIcon className="h-4 w-4 text-blue-500" />
                            <CheckIcon className="h-4 w-4 text-blue-500" />
                          </span>
                        )}

                        {showDelete === msg.id && (
                          <span
                            className="delete-message cursor-pointer ml-2"
                            onClick={() => deleteMessage(msg.id)}
                            aria-label="Delete message"
                          >
                            <XMarkIcon className="h-4 w-4 text-red-600" />
                          </span>
                        )}
                      </span>
                    )}
                  </span>
                </>
              )}

              {/* ---------- MESSAGE REACTIONS ---------- */}
              {msg.reactions && msg.reactions.length > 0 && (
                <div className="message-reactions" style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '4px',
                  marginTop: '8px'
                }}>
                  {msg.reactions.map((reaction, idx) => (
                    <span
                      key={idx}
                      className="reaction-emoji"
                      onClick={() => removeReactionFromMessage(msg.id, reaction.emoji)}
                      title={reaction.emoji}
                      style={{
                        display: 'inline-block',
                        padding: '2px 6px',
                        backgroundColor: 'rgba(0,0,0,0.1)',
                        borderRadius: '12px',
                        cursor: 'pointer',
                        fontSize: '14px',
                        transition: 'background-color 0.2s'
                      }}
                      onMouseEnter={(e) => e.target.style.backgroundColor = 'rgba(0,0,0,0.2)'}
                      onMouseLeave={(e) => e.target.style.backgroundColor = 'rgba(0,0,0,0.1)'}
                    >
                      {reaction.emoji}
                    </span>
                  ))}
                  <span
                    className="add-reaction-btn"
                    onClick={() => setShowReactionPicker(msg.id)}
                    title="Add reaction"
                    style={{
                      display: 'inline-block',
                      padding: '2px 6px',
                      backgroundColor: 'rgba(0,0,0,0.05)',
                      borderRadius: '12px',
                      cursor: 'pointer',
                      fontSize: '12px',
                      color: '#999'
                    }}
                  >
                    +
                  </span>
                </div>
              )}

              {showReactionPicker === msg.id && (
                <div style={{
                  marginTop: '8px',
                  padding: '8px',
                  backgroundColor: '#f5f5f5',
                  borderRadius: '8px'
                }}>
                  <div style={{
                    display: 'flex',
                    gap: '4px',
                    flexWrap: 'wrap'
                  }}>
                    {['👍', '❤️', '😂', '😮', '😢', '🔥', '✨', '🎉'].map((emoji) => (
                      <span
                        key={emoji}
                        onClick={() => addReactionToMessage(msg.id, emoji)}
                        style={{
                          fontSize: '20px',
                          cursor: 'pointer',
                          padding: '4px',
                          borderRadius: '4px',
                          transition: 'background-color 0.2s'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#e0e0e0'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                      >
                        {emoji}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {isTyping && (
          <div className="Chatt-Box typing-indicator">
            <p>{currentSender.name} is typing...</p>
          </div>
        )}
      </div>

      {/* ---------- FOOTER ---------- */}
      <div className="MMApss-Body-Foot">
        <div className="TTh-MM-TtaetBox">
          <div className="ool-taetga">
            {isRecording ? (
              <motion.div
                className="voice-recording-panel"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <motion.div
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ repeat: Infinity, duration: 0.6 }}
                >
                  <MicrophoneIcon className="h-5 w-5 text-red-600" />
                </motion.div>
                <div className="voice-bars">
                  <div className="voice-bar" />
                  <div className="voice-bar" />
                  <div className="voice-bar" />
                  <div className="voice-bar" />
                  <div className="voice-bar" />
                </div>
                <span className="recording-timer">{recordingTime}</span>
              </motion.div>
            ) : recordedAudioUrl ? (
              <div className="voice-preview" key={recordedAudioUrl}>
                <div className="voice-playback">
                  <span
                    onClick={togglePreviewPlayback}
                    className="fff-Controll cursor-pointer"
                  >
                    {previewIsPlaying ? (
                      <PauseIcon className="h-5 w-5 text-blue-600" />
                    ) : (
                      <PlayIcon className="h-5 w-5 text-blue-600" />
                    )}
                  </span>
                  <div className="voice-waveform">
                    {Array.from({ length: 20 }).map((_, i) => (
                      <div
                        key={i}
                        className={`voice-wave-bar ${
                          previewDuration > 0 &&
                          i <
                            Math.floor(
                              (previewCurrentTime / previewDuration) * 20
                            )
                            ? "active"
                            : ""
                        }`}
                      />
                    ))}
                  </div>
                  <span className="voice-time">
                    {previewIsPlaying
                      ? formatTime(previewCurrentTime)
                      : formatTime(previewDuration)}
                  </span>
                  <span
                    className="delete-voice cursor-pointer"
                    onClick={resetPreviewState}
                  >
                    <TrashIcon className="h-5 w-5 text-red-600" />
                  </span>
                </div>
                <audio
                  ref={(el) => (audioRefs.current["preview"] = el)}
                  src={recordedAudioUrl}
                  hidden
                  preload="metadata"
                  onTimeUpdate={() => {
                    if (audioRefs.current["preview"]) {
                      setPreviewCurrentTime(
                        audioRefs.current["preview"].currentTime
                      );
                    }
                  }}
                  onLoadedMetadata={() => {
                    if (audioRefs.current["preview"]) {
                      setPreviewDuration(audioRefs.current["preview"].duration);
                    }
                  }}
                  onEnded={() => {
                    setPreviewIsPlaying(false);
                    setPreviewCurrentTime(0);
                  }}
                />
              </div>
            ) : (
              <div className="ssaa-Tcc-Area">
                <textarea
                  ref={textareaRef}
                  placeholder="Type a message"
                  onInput={handleInput}
                  onKeyDown={handleKeyDown}
                  onFocus={() => setShowEmojiPicker(false)}
                  style={{ maxHeight: "150px", overflowY: "auto" }}
                  className="custom-scroll-bar"
                />

                {showEmojiPicker && (
                  <div className="emoji-picker-container" ref={emojiPickerRef}>
                    <Picker
                      data={data}
                      onEmojiSelect={addEmoji}
                      theme="light"
                    />
                  </div>
                )}

                <span>{wordCount}/100</span>
              </div>
            )}
          </div>
          <div className="GG-Cotrols">
            <div className="GG-Cotrols-Cont">
              <span onClick={() => setShowEmojiPicker((prev) => !prev)}>
                <FaceSmileIcon />
              </span>
              <span onClick={() => fileInputRef.current?.click()}>
                <PaperClipIcon className="h-6 w-6" />
              </span>

              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                style={{ display: "none" }}
              />
            </div>
            <div className="GG-Cotrols-Cont">
              {!messageText.trim() && !recordedAudioUrl && (
                <motion.span
                  onClick={toggleRecording}
                  className="cursor-pointer"
                  animate={
                    isRecording
                      ? { scale: [1, 1.2, 1], rotate: [0, 5, -5, 0] }
                      : {}
                  }
                  transition={
                    isRecording ? { repeat: Infinity, duration: 1.2 } : {}
                  }
                >
                  <MicrophoneIcon
                    className={`h-6 w-6 ${
                      isRecording ? "recording-active" : ""
                    }`}
                  />
                </motion.span>
              )}
              <span onClick={sendMessage} className="cursor-pointer">
                <PaperAirplaneIcon />
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Messaging;
