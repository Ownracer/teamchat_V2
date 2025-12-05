import React, { useState, useRef, useEffect } from 'react';
import { ArrowLeft, Phone, Video, MoreVertical, Paperclip, Mic, Send, Lightbulb, Trash2, Reply, X, Forward, Users, Pin, ChevronLeft, ChevronRight, PhoneOff } from 'lucide-react';
import VideoCall from './VideoCall';
import FilePreviewModal from './FilePreviewModal';
import ConfirmationModal from './ConfirmationModal';

const ChatWindow = ({ chat, chats, userStatuses, currentUser, onBack, onDeleteChat }) => {
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const [message, setMessage] = useState('');
    const [messages, setMessages] = useState([]);
    const [callRoomName, setCallRoomName] = useState(null); // State for active call room
    const [isVoiceCall, setIsVoiceCall] = useState(false);
    const [isInCall, setIsInCall] = useState(false); // Deprecated, but keeping for safety until full removal
    const [replyingTo, setReplyingTo] = useState(null);
    const [showMenu, setShowMenu] = useState(false);

    // Confirmation Modal State
    const [confirmation, setConfirmation] = useState({
        isOpen: false,
        title: '',
        message: '',
        onConfirm: () => { },
        isDanger: false,
        confirmText: 'Confirm'
    });

    // Forwarding State
    const [showForwardModal, setShowForwardModal] = useState(false);
    const [messageToForward, setMessageToForward] = useState(null);

    // Participants State
    const [showParticipantsModal, setShowParticipantsModal] = useState(false);
    const [participants, setParticipants] = useState([]);
    const [showAddMemberModal, setShowAddMemberModal] = useState(false);
    const [addMemberEmail, setAddMemberEmail] = useState('');

    // Pin State
    const [pinnedMessages, setPinnedMessages] = useState([]);
    const [activePinIndex, setActivePinIndex] = useState(0);
    const [activeCallMessageId, setActiveCallMessageId] = useState(null);

    // Toast State
    const [toast, setToast] = useState(null);
    const [fileToPreview, setFileToPreview] = useState(null);

    const handleFileSelect = (e) => {
        const file = e.target.files[0];
        if (file) {
            setFileToPreview(file);
        }
        // Reset input so same file can be selected again if needed
        e.target.value = null;
    };

    const handleSendFile = async (file, caption) => {
        setFileToPreview(null); // Close modal immediately

        const formData = new FormData();
        formData.append('file', file);

        try {
            // 1. Upload File
            const response = await fetch(`${API_URL}/upload`, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();

            const newMessage = {
                type: 'file',
                filename: file.name,
                fileUrl: data.url,
                size: (file.size / 1024 / 1024).toFixed(1) + ' MB',
                sender: 'me',
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                status: 'sent',
                text: caption || null // Add caption if provided
            };

            // 2. Save Message to Backend
            const msgResponse = await fetch(`${API_URL}/chats/${chat.id}/messages`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newMessage)
            });

            const savedMsg = await msgResponse.json();
            setMessages([...messages, savedMsg]);

        } catch (error) {
            console.error("File upload failed", error);
            alert("Failed to upload file");
        }
    };

    const showNotification = (message) => {
        setToast(message);
        setTimeout(() => setToast(null), 3000);
    };

    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    const lastMessagesRef = useRef("");

    useEffect(() => {
        lastMessagesRef.current = ""; // Reset on chat change

        const fetchMessages = () => {
            fetch(`${API_URL}/chats/${chat.id}/messages`)
                .then(res => res.json())
                .then(data => {
                    const dataStr = JSON.stringify(data);
                    if (dataStr !== lastMessagesRef.current) {
                        lastMessagesRef.current = dataStr;
                        setMessages(data);

                        const pinned = data.filter(m => m.isPinned);
                        if (JSON.stringify(pinned) !== JSON.stringify(pinnedMessages)) {
                            setPinnedMessages(pinned);
                            if (pinned.length > 0 && pinned.length > pinnedMessages.length) setActivePinIndex(pinned.length - 1);
                        }
                    }
                })
                .catch(err => console.error("Failed to fetch messages", err));
        };

        fetchMessages(); // Initial fetch
        const interval = setInterval(fetchMessages, 3000); // Poll every 3s

        return () => clearInterval(interval);
    }, [chat.id]); // Re-run when chat changes

    useEffect(() => {
        // Fetch participants if it's a group to get accurate count
        if (chat.type === 'group') {
            fetch(`${API_URL}/chats/${chat.id}/participants`)
                .then(res => res.json())
                .then(data => {
                    // Ensure current user is included in the list
                    if (currentUser && !data.some(p => p.id === currentUser.id)) {
                        data.push({
                            ...currentUser,
                            avatar: currentUser.avatar || `https://ui-avatars.com/api/?name=${currentUser.name}&background=random`
                        });
                    }
                    setParticipants(data);
                })
                .catch(err => console.error("Failed to fetch participants", err));
        }
    }, [chat.id, chat.type]);

    useEffect(scrollToBottom, [messages]);

    const handleSendMessage = () => {
        if (!message.trim()) return;

        const newMessage = {
            text: message,
            sender: 'me',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            status: 'sent',
            replyTo: replyingTo
        };

        fetch(`${API_URL}/chats/${chat.id}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newMessage)
        })
            .then(res => res.json())
            .then(savedMsg => {
                setMessages([...messages, savedMsg]);
                setMessage('');
                setReplyingTo(null);
            })
            .catch(err => console.error("Failed to send message", err));
    };

    const handleStartCall = () => {
        const roomName = `TeamChat-${chat.id}-${Date.now()}`;
        setCallRoomName(roomName);

        const callMessage = {
            text: "📞 Video Call started",
            type: 'call',
            callRoomName: roomName,
            sender: 'me',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            status: 'sent'
        };

        fetch(`${API_URL}/chats/${chat.id}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(callMessage)
        })
            .then(res => res.json())
            .then(savedMsg => {
                setMessages([...messages, savedMsg]);
                setActiveCallMessageId(savedMsg.id);
            })
            .catch(err => console.error("Failed to send call message", err));
    };

    const handleStartVoiceCall = () => {
        const roomName = `TeamChat-${chat.id}-${Date.now()}`;
        setCallRoomName(roomName);
        setIsVoiceCall(true);

        const callMessage = {
            text: "📞 Voice Call started",
            type: 'call',
            callRoomName: roomName,
            sender: 'me',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            status: 'sent',
            isVoice: true
        };

        fetch(`${API_URL}/chats/${chat.id}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(callMessage)
        })
            .then(res => res.json())
            .then(savedMsg => {
                setMessages([...messages, savedMsg]);
                setActiveCallMessageId(savedMsg.id);
            })
            .catch(err => console.error("Failed to send call message", err));
    };

    const handleLeaveCall = () => {
        setCallRoomName(null);
        setIsVoiceCall(false);
    };

    const handleEndMeeting = (msgId) => {
        setConfirmation({
            isOpen: true,
            title: 'End Call',
            message: 'Are you sure you want to end this call for everyone?',
            isDanger: true,
            confirmText: 'End Call',
            onConfirm: () => {
                fetch(`${API_URL}/chats/${chat.id}/messages/${msgId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: "Call Ended",
                        callStatus: "ended"
                    })
                })
                    .then(res => res.json())
                    .then(updatedMsg => {
                        setMessages(messages.map(m => m.id === updatedMsg.id ? updatedMsg : m));
                        if (activeCallMessageId === msgId) setActiveCallMessageId(null);
                    })
                    .catch(err => console.error("Failed to end call", err));
            }
        });
    };

    const handleForwardMessage = (targetChatId) => {
        if (!messageToForward) return;

        const forwardedMsg = {
            text: messageToForward.text,
            type: messageToForward.type,
            filename: messageToForward.filename,
            fileUrl: messageToForward.fileUrl,
            size: messageToForward.size,
            sender: 'me',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            status: 'sent',
            isForwarded: true
        };

        fetch(`${API_URL}/chats/${targetChatId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(forwardedMsg)
        })
            .then(() => {
                showNotification("Message forwarded!");
                setShowForwardModal(false);
                setMessageToForward(null);
            })
            .catch(err => console.error("Failed to forward message", err));
    };

    const handleDeleteMessage = (id, forEveryone) => {
        if (forEveryone) {
            fetch(`${API_URL}/chats/${chat.id}/messages/${id}`, {
                method: 'DELETE'
            })
                .then(() => {
                    setMessages(messages.filter(m => m.id !== id));
                    showNotification("Message deleted");
                })
                .catch(err => console.error("Failed to delete message", err));
        } else {
            // For "Delete for me", we might just hide it locally, but for MVP we'll remove it
            setMessages(messages.filter(m => m.id !== id));
        }
    };

    const handlePinMessage = (messageId) => {
        fetch(`${API_URL}/chats/${chat.id}/messages/${messageId}/pin`, {
            method: 'POST'
        })
            .then(res => res.json())
            .then(updatedMsg => {
                // Update local state
                const updatedMessages = messages.map(m => {
                    if (m.id === messageId) return { ...m, isPinned: updatedMsg.isPinned };
                    return m;
                });
                setMessages(updatedMessages);

                if (updatedMsg.isPinned) {
                    setPinnedMessages(prev => [...prev, updatedMsg]);
                    setActivePinIndex(pinnedMessages.length); // Switch to new pin
                    showNotification("Message pinned");
                } else {
                    setPinnedMessages(prev => {
                        const newPins = prev.filter(p => p.id !== messageId);
                        // Adjust index if needed
                        if (activePinIndex >= newPins.length) setActivePinIndex(Math.max(0, newPins.length - 1));
                        return newPins;
                    });
                    showNotification("Message unpinned");
                }
            })
            .catch(err => console.error("Failed to pin message", err));
    };

    const handleClearChat = () => {
        setConfirmation({
            isOpen: true,
            title: 'Clear Chat',
            message: 'Are you sure you want to clear this chat? All messages will be removed.',
            isDanger: true,
            confirmText: 'Clear',
            onConfirm: () => {
                fetch(`${API_URL}/chats/${chat.id}/messages`, {
                    method: 'DELETE'
                })
                    .then(() => {
                        setMessages([]);
                        setShowMenu(false);
                        showNotification("Chat cleared");
                    })
                    .catch(err => {
                        console.error("Failed to clear chat", err);
                        showNotification("Failed to clear chat");
                    });
            }
        });
    };

    const handleDeleteChannel = () => {
        setConfirmation({
            isOpen: true,
            title: 'Delete Channel',
            message: 'Are you sure you want to delete this channel? This action cannot be undone.',
            isDanger: true,
            confirmText: 'Delete',
            onConfirm: () => {
                onDeleteChat(chat.id);
            }
        });
    };

    const handleAnalyzeFile = async (filename) => {
        showNotification(`Analyzing ${filename}...`);
        try {
            const response = await fetch(`${API_URL}/analyze-file`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: filename,
                    content_preview: "File content placeholder" // In a real app, we'd send actual content
                })
            });
            const data = await response.json();

            if (data.is_idea) {
                showNotification("File saved to Idea Hub! 💡");
            } else {
                showNotification("Analysis complete (Not an idea)");
            }
        } catch (error) {
            console.error("Analysis failed", error);
            showNotification("Analysis failed");
        }
    };

    const handleAnalyzeMessage = async (text, sender) => {
        showNotification("Analyzing message...");
        try {
            const response = await fetch(`${API_URL}/analyze-message`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    sender: sender
                })
            });
            const data = await response.json();

            if (data.is_idea) {
                showNotification("Idea saved to Idea Hub! 💡");
            } else {
                showNotification("Analysis complete (Not an idea)");
            }
        } catch (error) {
            console.error("Analysis failed", error);
            showNotification("Analysis failed");
        }
    };

    const handleAddMember = () => {
        setShowAddMemberModal(true);
    };

    const submitAddMember = () => {
        if (addMemberEmail) {
            fetch(`${API_URL}/chats/${chat.id}/participants`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: addMemberEmail })
            })
                .then(async res => {
                    if (!res.ok) {
                        const err = await res.json();
                        throw new Error(err.detail || "Failed to add member");
                    }
                    return res.json();
                })
                .then(data => {
                    showNotification(`Added ${data.user.name} to the group!`);
                    setParticipants([...participants, data.user]);
                    setShowAddMemberModal(false);
                    setAddMemberEmail('');
                })
                .catch(err => {
                    console.error("Failed to add member", err);
                    showNotification(err.message);
                });
        }
    };

    const nextPin = (e) => {
        e.stopPropagation();
        setActivePinIndex((prev) => (prev + 1) % pinnedMessages.length);
    };

    const prevPin = (e) => {
        e.stopPropagation();
        setActivePinIndex((prev) => (prev - 1 + pinnedMessages.length) % pinnedMessages.length);
    };

    return (
        <div className="flex flex-col h-full bg-[#e5ddd5] relative">
            {callRoomName && (
                <VideoCall
                    roomName={callRoomName}
                    userName={currentUser?.name || "Guest"}
                    onClose={handleLeaveCall}
                    isVoiceOnly={isVoiceCall}
                />
            )}

            {/* Toast Notification */}
            {toast && (
                <div className="absolute top-20 left-1/2 transform -translate-x-1/2 bg-black bg-opacity-80 text-white px-4 py-2 rounded-full text-sm shadow-lg z-50 animate-fade-in-down transition-all">
                    {toast}
                </div>
            )}

            {/* Header */}
            <div className="h-16 px-4 flex items-center justify-between bg-white border-b border-gray-200 shadow-sm z-10 relative">
                <div className="flex items-center cursor-pointer hover:bg-gray-50 rounded-lg p-1 transition-colors" onClick={() => chat.type === 'group' && setShowParticipantsModal(true)}>
                    <button onClick={(e) => { e.stopPropagation(); onBack(); }} className="md:hidden mr-2 text-gray-600">
                        <ArrowLeft size={24} />
                    </button>
                    <img src={chat.avatar} alt={chat.name} className="w-10 h-10 rounded-full mr-3" />
                    <div>
                        <h3 className="font-semibold text-gray-800">{chat.name}</h3>
                        <span className="text-xs text-gray-500">
                            {chat.type === 'group'
                                ? `${participants.length || chat.participants?.length || chat.members || 1} members`
                                : (userStatuses[chat.id]?.status === 'online' ? 'Online' : `Last seen ${userStatuses[chat.id]?.lastSeen || 'recently'}`)}
                        </span>
                    </div>
                </div>
                <div className="flex items-center space-x-4 text-teal-600">
                    <button onClick={() => { setIsVoiceCall(false); handleStartCall(); }}><Video size={22} /></button>
                    <button onClick={handleStartVoiceCall}><Phone size={20} /></button>
                    <div className="relative">
                        <button onClick={() => setShowMenu(!showMenu)} className="text-gray-600"><MoreVertical size={20} /></button>
                        {showMenu && (
                            <div className="absolute right-0 top-10 bg-white shadow-lg rounded-lg py-2 w-48 z-20 border border-gray-100">
                                <button onClick={() => setShowParticipantsModal(true)} className="w-full text-left px-4 py-2 hover:bg-gray-50 text-gray-700 text-sm">View Participants</button>
                                <button onClick={handleClearChat} className="w-full text-left px-4 py-2 hover:bg-gray-50 text-gray-700 text-sm">Clear Chat</button>
                                <button onClick={handleDeleteChannel} className="w-full text-left px-4 py-2 hover:bg-gray-50 text-red-600 text-sm">Delete Channel</button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Pinned Message Header */}
            {pinnedMessages.length > 0 && (
                <div className="bg-gray-100 px-4 py-2 flex items-center justify-between border-b border-gray-200 sticky top-0 z-0 cursor-pointer" onClick={() => {
                    const currentPin = pinnedMessages[activePinIndex];
                    if (currentPin) {
                        const element = document.getElementById(`msg-${currentPin.id}`);
                        if (element) {
                            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            element.classList.add('bg-yellow-100'); // Highlight effect
                            setTimeout(() => element.classList.remove('bg-yellow-100'), 2000);
                        } else {
                            showNotification("Message not loaded or found");
                        }
                    }
                }}>
                    <div className="flex items-center space-x-2 overflow-hidden flex-1">
                        <Pin size={16} className="text-teal-600 flex-shrink-0" />
                        <div className="flex flex-col flex-1 min-w-0">
                            <span className="text-xs font-bold text-teal-600">
                                Pinned Message {pinnedMessages.length > 1 && `(${activePinIndex + 1}/${pinnedMessages.length})`}
                            </span>
                            <span className="text-sm text-gray-700 truncate">
                                {pinnedMessages[activePinIndex]?.text || pinnedMessages[activePinIndex]?.filename}
                            </span>
                        </div>
                    </div>

                    <div className="flex items-center space-x-2 ml-2">
                        {pinnedMessages.length > 1 && (
                            <div className="flex items-center bg-gray-200 rounded-lg">
                                <button onClick={prevPin} className="p-1 hover:bg-gray-300 rounded-l-lg text-gray-600">
                                    <ChevronLeft size={16} />
                                </button>
                                <button onClick={nextPin} className="p-1 hover:bg-gray-300 rounded-r-lg text-gray-600">
                                    <ChevronRight size={16} />
                                </button>
                            </div>
                        )}
                        <button onClick={(e) => { e.stopPropagation(); handlePinMessage(pinnedMessages[activePinIndex].id); }} className="text-gray-500 hover:text-gray-700 p-1">
                            <X size={16} />
                        </button>
                    </div>
                </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-opacity-50" style={{ backgroundImage: 'url("https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png")' }}>
                {chat.createdBy && (
                    <div className="flex justify-center mb-6">
                        <div className="bg-yellow-100 text-yellow-800 text-xs px-3 py-1 rounded-full shadow-sm border border-yellow-200">
                            This group was created by {chat.createdBy.name} ({chat.createdBy.email})
                        </div>
                    </div>
                )}
                {messages.map((msg) => (
                    <div key={msg.id} id={`msg-${msg.id}`} className={`flex ${msg.sender === 'me' ? 'justify-end' : 'justify-start'} group/msg transition-colors duration-500 rounded-lg`}>
                        <div className={`max-w-[70%] rounded-lg px-4 py-2 shadow-sm relative ${msg.sender === 'me' ? 'bg-teal-100 rounded-tr-none' : 'bg-white rounded-tl-none'}`}>

                            {/* Message Actions Dropdown Trigger (Hover) */}
                            {/* Removed separate trigger, now integrated into actions menu */}

                            {/* Reply Context */}
                            {msg.replyTo && (
                                <div className="mb-2 p-2 bg-black bg-opacity-5 rounded text-xs border-l-4 border-teal-500">
                                    <p className="font-bold text-teal-700">{msg.replyTo.sender === 'me' ? 'You' : chat.name}</p>
                                    <p className="truncate text-gray-600">{msg.replyTo.text || msg.replyTo.filename}</p>
                                </div>
                            )}

                            {/* Forwarded Label */}
                            {msg.isForwarded && (
                                <div className="flex items-center text-xs text-gray-500 mb-1 italic">
                                    <Forward size={10} className="mr-1" /> Forwarded
                                </div>
                            )}

                            {/* Message Content */}
                            {msg.type === 'file' ? (
                                <div className="flex items-center space-x-3">
                                    <div className="bg-red-100 p-2 rounded-lg">
                                        <Paperclip className="text-red-500" size={24} />
                                    </div>
                                    <div
                                        className="cursor-pointer hover:bg-gray-50 p-1 rounded transition-colors"
                                        onClick={async (e) => {
                                            e.stopPropagation(); // Prevent triggering other clicks
                                            if (msg.fileUrl) {
                                                try {
                                                    const response = await fetch(msg.fileUrl);
                                                    if (!response.ok) throw new Error('Download failed');

                                                    const blob = await response.blob();
                                                    const url = window.URL.createObjectURL(blob);
                                                    const link = document.createElement('a');
                                                    link.href = url;
                                                    link.download = msg.filename; // This forces download to default folder
                                                    document.body.appendChild(link);
                                                    link.click();
                                                    document.body.removeChild(link);
                                                    window.URL.revokeObjectURL(url);
                                                } catch (error) {
                                                    console.error("Download error:", error);
                                                    alert("Failed to download file. Please try again.");
                                                }
                                            } else {
                                                alert(`File URL not found for ${msg.filename}`);
                                            }
                                        }}
                                    >
                                        <p className="font-medium text-gray-800">{msg.filename}</p>
                                        <p className="text-xs text-gray-500">{msg.size}</p>
                                    </div>
                                    <button className="opacity-0 group-hover/msg:opacity-100 absolute -left-10 top-2 bg-yellow-100 text-yellow-700 p-1.5 rounded-full shadow-sm hover:bg-yellow-200 transition-opacity" title="Mark as Idea" onClick={() => handleAnalyzeFile(msg.filename)}>
                                        <Lightbulb size={16} />
                                    </button>
                                </div>
                            ) : msg.type === 'call' ? (
                                <div className="flex flex-col space-y-2 p-2 w-full">
                                    <div className={`flex items-center justify-center space-x-2 font-medium ${msg.callStatus === 'ended' ? 'text-gray-500' : 'text-gray-800'}`}>
                                        {msg.callStatus === 'ended' ? <PhoneOff size={20} /> : (msg.isVoice ? <Phone size={20} className="text-teal-600" /> : <Video size={20} className="text-teal-600" />)}
                                        <span>{msg.callStatus === 'ended' ? "Call Ended" : (msg.isVoice ? "Voice Call started" : "Video Call started")}</span>
                                    </div>
                                    {msg.callStatus !== 'ended' && (
                                        <div className="flex flex-col space-y-1 w-full">
                                            <button
                                                onClick={() => {
                                                    setCallRoomName(msg.callRoomName);
                                                    setIsVoiceCall(msg.isVoice);
                                                }}
                                                className="bg-teal-500 text-white px-4 py-2 rounded-full text-sm font-bold hover:bg-teal-600 transition-colors w-full"
                                            >
                                                Join Call
                                            </button>
                                            {msg.sender === 'me' && (
                                                <button
                                                    onClick={() => handleEndMeeting(msg.id)}
                                                    className="bg-red-100 text-red-600 px-4 py-1 rounded-full text-xs font-semibold hover:bg-red-200 transition-colors w-full"
                                                >
                                                    End for Everyone
                                                </button>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="relative">
                                    <p className="text-sm text-gray-800">{msg.text}</p>
                                    <button className="opacity-0 group-hover/msg:opacity-100 absolute -left-10 top-0 bg-yellow-100 text-yellow-700 p-1.5 rounded-full shadow-sm hover:bg-yellow-200 transition-opacity" title="Mark as Idea" onClick={() => handleAnalyzeMessage(msg.text, msg.sender)}>
                                        <Lightbulb size={16} />
                                    </button>
                                </div>
                            )}

                            {/* Metadata & Actions */}
                            <div className="flex justify-between items-center mt-1 space-x-2">
                                <span className="text-[10px] text-gray-500">{msg.time}</span>
                                {msg.sender === 'me' && <span className="text-teal-500 text-[10px]">✓✓</span>}
                            </div>

                            {/* Message Actions (Reply/Delete/Forward/Pin) - Visible on Hover */}
                            <div className={`absolute ${msg.sender === 'me' ? '-left-36' : '-right-36'} top-0 opacity-0 group-hover/msg:opacity-100 flex space-x-1 bg-white shadow-sm rounded-lg p-1 transition-opacity z-10`}>
                                <button onClick={() => setReplyingTo(msg)} className="p-1 hover:bg-gray-100 rounded text-gray-600" title="Reply">
                                    <Reply size={14} />
                                </button>
                                <button onClick={() => { setMessageToForward(msg); setShowForwardModal(true); }} className="p-1 hover:bg-gray-100 rounded text-gray-600" title="Forward">
                                    <Forward size={14} />
                                </button>
                                <button
                                    onClick={() => handlePinMessage(msg.id)}
                                    className={`p-1 hover:bg-gray-100 rounded ${msg.isPinned ? 'text-teal-600' : 'text-gray-600'}`}
                                    title={msg.isPinned ? "Unpin" : "Pin"}
                                >
                                    <Pin size={14} />
                                </button>
                                <button onClick={() => handleDeleteMessage(msg.id, true)} className="p-1 hover:bg-gray-100 rounded text-red-500" title="Delete">
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Reply Preview */}
            {
                replyingTo && (
                    <div className="bg-gray-50 px-4 py-2 border-t border-gray-200 flex justify-between items-center">
                        <div className="border-l-4 border-teal-500 pl-2">
                            <p className="text-xs font-bold text-teal-600">Replying to {replyingTo.sender === 'me' ? 'yourself' : chat.name}</p>
                            <p className="text-sm text-gray-600 truncate">{replyingTo.text || replyingTo.filename}</p>
                        </div>
                        <button onClick={() => setReplyingTo(null)} className="text-gray-500 hover:text-gray-700">
                            <X size={18} />
                        </button>
                    </div>
                )
            }

            {/* File Preview Modal */}
            <FilePreviewModal
                file={fileToPreview}
                onClose={() => setFileToPreview(null)}
                onSend={handleSendFile}
                onAddFile={() => document.getElementById('file-upload').click()}
            />

            {/* Input Area */}
            <div className="p-3 bg-gray-100 flex items-center space-x-2 z-20 relative border-t border-gray-200">
                <input
                    type="file"
                    id="file-upload"
                    className="hidden"
                    onChange={handleFileSelect}
                />
                <button
                    className="text-gray-500 hover:text-gray-700"
                    onClick={() => document.getElementById('file-upload').click()}
                >
                    <Paperclip size={24} />
                </button>
                <div className="flex-1 bg-white rounded-full flex items-center px-4 py-2 border border-gray-200">
                    <input
                        type="text"
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                        placeholder="Type a message"
                        className="flex-1 bg-transparent focus:outline-none text-sm"
                    />
                </div>
                {message ? (
                    <button onClick={handleSendMessage} className="bg-teal-500 text-white p-2 rounded-full hover:bg-teal-600 transition-colors">
                        <Send size={20} />
                    </button>
                ) : (
                    <button className="text-gray-500 hover:text-gray-700">
                        <Mic size={24} />
                    </button>
                )}
            </div>

            {/* Forward Modal */}
            {showForwardModal && (
                <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl w-full max-w-sm shadow-2xl flex flex-col max-h-[80vh]">
                        <div className="p-4 border-b border-gray-200 flex justify-between items-center">
                            <h3 className="text-lg font-bold text-gray-800">Forward to...</h3>
                            <button onClick={() => setShowForwardModal(false)} className="text-gray-500 hover:text-gray-700">
                                <X size={20} />
                            </button>
                        </div>
                        <div className="flex-1 overflow-y-auto p-2">
                            {chats.map((c) => (
                                <div
                                    key={c.id}
                                    onClick={() => handleForwardMessage(c.id)}
                                    className="flex items-center p-3 hover:bg-gray-50 rounded-lg cursor-pointer transition-colors"
                                >
                                    <img src={c.avatar} alt={c.name} className="w-10 h-10 rounded-full mr-3" />
                                    <span className="font-medium text-gray-800">{c.name}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Add Member Modal */}
            {showAddMemberModal && (
                <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl w-full max-w-sm shadow-2xl flex flex-col p-6 animate-scale-in">
                        <h3 className="text-lg font-bold text-gray-800 mb-4">Add Member</h3>
                        <p className="text-sm text-gray-600 mb-4">Enter the email of the user you want to add to this group.</p>
                        <input
                            type="email"
                            value={addMemberEmail}
                            onChange={(e) => setAddMemberEmail(e.target.value)}
                            placeholder="user@example.com"
                            className="w-full border border-gray-300 rounded-lg px-4 py-2 mb-6 focus:outline-none focus:ring-2 focus:ring-teal-500"
                            autoFocus
                        />
                        <div className="flex justify-end space-x-3">
                            <button
                                onClick={() => setShowAddMemberModal(false)}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={submitAddMember}
                                className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors font-medium"
                            >
                                Add
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Group Info Side Panel */}
            {showParticipantsModal && (
                <div className="absolute top-0 right-0 h-full w-80 bg-[#111b21] shadow-xl z-20 border-l border-gray-700 flex flex-col animate-slide-in-right text-gray-300">
                    {/* Header */}
                    <div className="h-16 px-4 flex items-center justify-between bg-[#202c33] border-b border-gray-700">
                        <div className="flex items-center">
                            <button onClick={() => setShowParticipantsModal(false)} className="mr-4 text-gray-400 hover:text-white">
                                <X size={24} />
                            </button>
                            <h3 className="text-lg font-medium text-white">Group info</h3>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto custom-scrollbar">
                        {/* Group Profile */}
                        <div className="flex flex-col items-center p-6 bg-[#111b21] border-b border-gray-800">
                            <img src={chat.avatar} alt={chat.name} className="w-32 h-32 rounded-full mb-4 object-cover" />
                            <h2 className="text-xl font-semibold text-white mb-1 text-center">{chat.name}</h2>
                            <p className="text-sm text-gray-500 mb-2">Group • {participants.length} members</p>
                        </div>

                        {/* Description/About (Mock) */}
                        <div className="p-4 bg-[#111b21] border-b border-gray-800">
                            <p className="text-sm text-teal-500 mb-1">Description</p>
                            <p className="text-sm text-gray-300">Welcome to the official group for {chat.name}. Share ideas and collaborate!</p>
                        </div>

                        {/* Members List */}
                        <div className="p-2">
                            <div className="px-4 py-2 text-sm text-teal-500 font-medium">{participants.length} members</div>

                            {/* Add Member Option */}
                            <div className="flex items-center p-3 hover:bg-[#202c33] rounded-lg cursor-pointer transition-colors" onClick={handleAddMember}>
                                <div className="w-10 h-10 rounded-full bg-teal-600 flex items-center justify-center mr-3">
                                    <Users size={20} className="text-white" />
                                </div>
                                <div className="flex-1">
                                    <p className="text-white font-medium">Add member</p>
                                </div>
                            </div>

                            {/* Participants */}
                            {participants.map((p) => (
                                <div key={p.id} className="flex items-center p-3 hover:bg-[#202c33] rounded-lg cursor-pointer transition-colors group">
                                    <img src={p.avatar} alt={p.name} className="w-10 h-10 rounded-full mr-3" />
                                    <div className="flex-1 min-w-0">
                                        <div className="flex justify-between items-baseline">
                                            <p className="text-white font-medium truncate">
                                                {p.id === currentUser?.id ? "You" : p.name}
                                            </p>
                                            {/* Admin Tag Mock */}
                                            {p.id === 1 && <span className="text-xs text-teal-500 border border-teal-500 px-1 rounded ml-2">Group admin</span>}
                                        </div>
                                        <p className="text-xs text-gray-500 truncate">
                                            {p.id === currentUser?.id ? "Available" : (userStatuses[p.id]?.status === 'online' ? 'Online' : `Last seen ${userStatuses[p.id]?.lastSeen || 'recently'}`)}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
            {/* Confirmation Modal */}
            <ConfirmationModal
                isOpen={confirmation.isOpen}
                onClose={() => setConfirmation({ ...confirmation, isOpen: false })}
                onConfirm={confirmation.onConfirm}
                title={confirmation.title}
                message={confirmation.message}
                isDanger={confirmation.isDanger}
                confirmText={confirmation.confirmText}
            />
        </div>
    );
};

export default ChatWindow;
