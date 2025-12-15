import React, { useState, useRef, useEffect, useCallback } from "react";
import "./Messages.css";
import {
  MagnifyingGlassIcon,
  CheckIcon,
  ChatBubbleOvalLeftEllipsisIcon,
  XMarkIcon,
  BackspaceIcon,
} from "@heroicons/react/24/outline";
import { ChatBubbleBottomCenterTextIcon } from "@heroicons/react/24/solid";
import { motion, AnimatePresence } from "framer-motion";
import MembImg1 from "./../Img/memberIcon1.jpg";
import Messaging from "../Messaging";
import chatImg from "../../../assets/Img/NochatIcon.png";
import StartMsgImg from "../Img/NoMessage.svg";
import { WEBSOCKET_URL } from "../../../config";
import { fetchAllUsers, fetchUserChats, createDirectChat, fetchChatConversations } from "../../CompanyDashboard/Recruitment/ApiService";

const Messages = () => {
  const user = JSON.parse(localStorage.getItem("user"));
  const currentUserId = user?.id;
  const jwtToken = localStorage.getItem("accessToken");

  // Assume these props from parent/context
  const [showNewMessage, setShowNewMessage] = useState(false);
  const [showChatSearch, setShowChatSearch] = useState(false);
  const [searchTermNew, setSearchTermNew] = useState("");
  const [searchTermActive, setSearchTermActive] = useState("");
  const [selectedChat, setSelectedChat] = useState(null);
  const [contacts, setContacts] = useState([]); // From get_users
  const [activeChats, setActiveChats] = useState([]); // From get_chats
  const [isConnected, setIsConnected] = useState(false);

  const newMessageRef = useRef(null);
  const chatSearchRef = useRef(null);
  const socketRef = useRef(null);

  // Load initial data via API instead of WebSocket
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        // Fetch users via API service
        const usersResponse = await fetchAllUsers();
        const userList = usersResponse.results.map((user) => ({
          id: user.id.toString(),
          name: user.display_name || user.username,
          avatar: user.profile_image_url || null,
          email: user.email,
          online: user.is_online || false,
        }));
        setContacts(userList);

        // Fetch chats via API service
        const chatsResponse = await fetchChatConversations();
        const chatList = chatsResponse.results
          .filter((chat) => chat.participants && Array.isArray(chat.participants))
          .map((chat) => {
            const otherParticipant = chat.participants.find(
              (p) => p.id != currentUserId
            );
            return {
              id: chat.id,
              userId: otherParticipant ? otherParticipant.id.toString() : null,
              name: otherParticipant
                ? otherParticipant.display_name || otherParticipant.username
                : chat.title || "Unknown",
              avatar: otherParticipant?.profile_image_url || null,
              time: new Date(chat.last_message_at || chat.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              }),
              lastMessage: chat.last_message?.content || "No messages yet",
              unreadCount: chat.unread_count || 0,
              read: (chat.unread_count || 0) === 0,
              type: chat.conversation_type,
            };
          });
        setActiveChats(chatList);
      } catch (error) {
        console.error('Error loading initial data:', error);
      }
    };

    if (jwtToken && currentUserId) {
      loadInitialData();
    }
  }, [jwtToken, currentUserId]);

  const toggleNewMessage = () => setShowNewMessage(!showNewMessage);

  const filteredChats = contacts.filter(
    (chat) =>
      chat.name.toLowerCase().includes(searchTermNew.toLowerCase()) ||
      chat.id.toLowerCase().includes(searchTermNew.toLowerCase())
  );

  const filteredMessages = activeChats.filter(
    (msg) =>
      msg.name.toLowerCase().includes(searchTermActive.toLowerCase()) ||
      msg.id.toLowerCase().includes(searchTermActive.toLowerCase()) ||
      msg.lastMessage.toLowerCase().includes(searchTermActive.toLowerCase())
  );

  const handleChatSelect = useCallback(
    async (chat) => {
      try {
        // For new chat: create direct chat using API service
        const chatData = await createDirectChat(parseInt(chat.id));
        const chatName = chat.name;
        const existing = activeChats.find((c) => c.id === chatData.id);
        if (!existing) {
          setActiveChats((prev) => [
            ...prev,
            {
              id: chatData.id,
              userId: chat.id,
              name: chatName,
              avatar: chat.avatar,
              time: new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              }),
              lastMessage: "New chat started",
              unreadCount: 0,
              read: true,
            },
          ]);
        }

        setSelectedChat({
          id: parseInt(chat.id),
          name: chatName,
          initials: chatName.charAt(0),
          avatar: chat.avatar,
          staffId: chat.id,
          chatId: chatData.id, // Pass chatId to Messaging
        });

        setShowNewMessage(false);
      } catch (error) {
        console.error("Failed to create chat:", error);
      }
    },
    [activeChats, currentUserId]
  );

  const updateLastMessage = useCallback((chatId, message) => {
    setActiveChats((prev) =>
      prev.map((chat) =>
        chat.id === chatId
          ? {
              ...chat,
              lastMessage: message,
              time: new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              }),
              read: false,
            }
          : chat
      )
    );
  }, []);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        newMessageRef.current &&
        !newMessageRef.current.contains(event.target)
      ) {
        setShowNewMessage(false);
      }
      if (
        chatSearchRef.current &&
        !chatSearchRef.current.contains(event.target)
      ) {
        setShowChatSearch(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // For existing chats select (update to use chat.id as user id, but pass chat.chatId)
  const handleExistingChatSelect = useCallback((chat) => {
    setSelectedChat({
      id: chat.userId || chat.id, // Use userId if available
      name: chat.name,
      initials: chat.name.charAt(0),
      avatar: chat.avatar,
      staffId: chat.userId || chat.id,
      chatId: chat.id, // API chat.id
    });
  }, []);

  const handleCloseMessaging = () => {
    setSelectedChat(null);
  };

  return (
    <div className="Messages-Secs">
      <div className="Messg-Part-1">
        <div className="Messg-Part-1-Top">
          <h3>{showNewMessage ? "New message" : "Messages"}</h3>
          <div className="Mmesa-Btns">
            <span onClick={toggleNewMessage}>
              {showNewMessage ? (
                <XMarkIcon />
              ) : (
                <ChatBubbleOvalLeftEllipsisIcon />
              )}
            </span>
            <span onClick={() => setShowChatSearch(!showChatSearch)}>
              {showChatSearch ? <XMarkIcon /> : <MagnifyingGlassIcon />}
            </span>
          </div>
        </div>

        <div className="Messg-Part-1-Main custom-scroll-bar">
          {/* New Message Panel */}
          <AnimatePresence initial={false}>
            {showNewMessage && (
              <motion.div
                className="See_All_SttaG"
                ref={newMessageRef}
                initial={{ height: 0, y: -20 }}
                animate={{ height: "auto", y: 0 }}
                exit={{ height: 0, y: -20 }}
                transition={{ duration: 0.35, ease: "easeInOut" }}
              >
                <div className="See_All_SttaG_Main">
                  <div className="See_All_SttaG_LIst_Top">
                    <div className="Seachh-EcM-Main">
                      <span>
                        <MagnifyingGlassIcon />
                      </span>
                      <input
                        type="text"
                        placeholder="Search by name or ID"
                        value={searchTermNew}
                        onChange={(e) => setSearchTermNew(e.target.value)}
                      />
                      {searchTermNew && (
                        <span
                          className="searhc-CloSee"
                          onClick={() => setSearchTermNew("")}
                        >
                          <BackspaceIcon />
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="See_All_SttaG_LIst custom-scroll-bar">
                    <ul className="Chatth-Ul">
                      {filteredChats.length > 0 ? (
                        filteredChats.map((chat) => (
                          <li
                            className="All-Caht-Li"
                            key={chat.id}
                            onClick={() => handleChatSelect(chat)}
                            style={{ cursor: "pointer" }}
                          >
                            <div className="All-Caht-Li-1">
                              {chat.avatar ? (
                                <img src={chat.avatar} alt={chat.name} />
                              ) : (
                                <span>{chat.name.charAt(0)}</span>
                              )}
                              {chat.online && (
                                <span className="online-dot"></span>
                              )}{" "}
                              {/* Add CSS for green dot */}
                            </div>
                            <div className="All-Caht-Li-2">
                              <div className="All-Caht-Li-2-Main">
                                <h3>
                                  <b>{chat.name}</b>
                                </h3>
                                <p>
                                  <b>ID: {chat.id}</b>{" "}
                                  {chat.email ? (
                                    <small>{chat.email}</small>
                                  ) : null}
                                </p>
                              </div>
                            </div>
                          </li>
                        ))
                      ) : (
                        <p className="No-results">No results found</p>
                      )}
                    </ul>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Chat Search Panel */}
          <AnimatePresence>
            {showChatSearch && (
              <motion.div
                className="MM-OIkaiks-Top"
                ref={chatSearchRef}
                initial={{ scaleY: 0, opacity: 0 }}
                animate={{ scaleY: 1, opacity: 1 }}
                exit={{ scaleY: 0, opacity: 0 }}
                transition={{ duration: 0.3, ease: "easeInOut" }}
                style={{ originY: 0 }}
              >
                <div className="Seachh-EcM-Main">
                  <span>
                    <MagnifyingGlassIcon />
                  </span>
                  <input
                    type="text"
                    placeholder="Search for chat"
                    value={searchTermActive}
                    onChange={(e) => setSearchTermActive(e.target.value)}
                  />
                  {searchTermActive && (
                    <span
                      className="searhc-CloSee"
                      onClick={() => setSearchTermActive("")}
                    >
                      <BackspaceIcon />
                    </span>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Messages List */}
          <div className="MM-OIkaiks">
            <h2 className="kmj-Header">
              <span>
                <ChatBubbleBottomCenterTextIcon /> All Messages QWERTY
              </span>
              <b>{activeChats.length}</b>
            </h2>

            {activeChats.length > 0 ? (
              <ul className="Chatth-Ul">
                {filteredMessages.map((msg) => (
                  <li
                    className="All-Caht-Li"
                    key={msg.id}
                    onClick={() => handleExistingChatSelect(msg)}
                    style={{ cursor: "pointer" }}
                  >
                    <div className="All-Caht-Li-1">
                      {msg.avatar ? (
                        <img src={msg.avatar} alt={msg.name} />
                      ) : (
                        <span>{msg.name.charAt(0)}</span>
                      )}
                    </div>
                    <div className="All-Caht-Li-2">
                      <div className="All-Caht-Li-2-Main">
                        <h3>
                          <b>{msg.name}</b>
                          <span>{msg.time}</span>
                        </h3>
                        <p>
                          <b>{msg.lastMessage}</b>
                          <span className="Icomn-Part">
                            {msg.read ? (
                              <span className="Sppan-Icon">
                                <CheckIcon />
                                <CheckIcon />
                              </span>
                            ) : (
                              <span className="unread-badge">
                                {msg.unreadCount > 99 ? "99+" : msg.unreadCount}
                              </span>
                            )}
                          </span>
                        </p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="NOn-Ujs">
                <img src={chatImg} />
                <p className="No-results">No Chat yet</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="Messg-Part-2">
        <div className="Messg-Part-2-Main">
          <div className="Messg-Part-2-Main-Mannso">
            {selectedChat ? (
              <Messaging
                closeMessaging={handleCloseMessaging}
                sender={selectedChat}
                jwtToken={jwtToken}
                currentUserId={currentUserId}
                chatId={selectedChat.chatId}
                onSendMessage={updateLastMessage}
              />
            ) : (
              <div className="lol-NOn-Ujs">
                <img src={StartMsgImg} />
                <p className="No-results">Select a chat to start messaging</p>
              </div>
            )}
          </div>
        </div>
      </div>

    </div>
  );
};

export default Messages;
