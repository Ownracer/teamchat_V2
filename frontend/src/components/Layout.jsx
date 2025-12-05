import React, { useState, useEffect } from 'react';
import Sidebar from './Sidebar';
import ChatWindow from './ChatWindow';
import IdeaHub from './IdeaHub';
import CalendarView from './CalendarView';
import BottomNav from './BottomNav';
import Login from './Login';
import Register from './Register';
import Profile from './Profile';
import ConfirmationModal from './ConfirmationModal';
import { Edit2 } from 'lucide-react';

const Layout = () => {
  const [user, setUser] = useState(null); // Auth state
  const [isRegistering, setIsRegistering] = useState(false);
  const [selectedChat, setSelectedChat] = useState(null);
  const [activeTab, setActiveTab] = useState('chats'); // chats, ideas, calendar, profile

  // Confirmation Modal State
  const [confirmation, setConfirmation] = useState({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: () => { },
    isDanger: false
  });

  // Lifted Chats State
  const [chats, setChats] = useState([]);
  const [userStatuses, setUserStatuses] = useState({}); // userId -> {status, lastSeen}

  // WebSocket Connection
  useEffect(() => {
    if (user) {
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const wsUrl = apiUrl.replace('http', 'ws');
      const ws = new WebSocket(`${wsUrl}/ws/${user.id}`);

      ws.onopen = () => {
        console.log("Connected to WebSocket");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'status_update') {
            setUserStatuses(prev => ({
              ...prev,
              [data.userId]: { status: data.status, lastSeen: new Date().toLocaleTimeString() }
            }));
          }
        } catch (e) {
          console.error("Error parsing WS message", e);
        }
      };

      return () => {
        ws.close();
      };
    }
  }, [user]);

  // Fetch chats on mount
  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${apiUrl}/chats`)
      .then(res => res.json())
      .then(data => {
        console.log("Fetched chats:", data);
        setChats(data);
      })
      .catch(err => console.error("Failed to fetch chats", err));
  }, [user]);

  // Public Groups State
  const [publicGroups, setPublicGroups] = useState([]);

  // Fetch public groups
  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    fetch(`${apiUrl}/chats/public`)
      .then(res => res.json())
      .then(data => setPublicGroups(data))
      .catch(err => console.error("Failed to fetch public groups", err));
  }, [chats]); // Refresh when chats change (e.g. after creating a group)

  // Auth Flow
  if (!user) {
    if (isRegistering) {
      return <Register onRegister={(userData) => setUser(userData)} onSwitchToLogin={() => setIsRegistering(false)} />;
    }
    return <Login onLogin={(userData) => setUser(userData)} onSwitchToRegister={() => setIsRegistering(true)} />;
  }

  const handleSelectChat = (chat) => {
    // Mark as read (Optimistic update)
    const updatedChats = chats.map(c =>
      c.id === chat.id ? { ...c, unread: 0 } : c
    );
    setChats(updatedChats);
    setSelectedChat({ ...chat, unread: 0 });
  };

  const handleDeleteChat = (chatId) => {
    setConfirmation({
      isOpen: true,
      title: 'Delete Chat',
      message: 'Are you sure you want to delete this chat? This action cannot be undone.',
      isDanger: true,
      onConfirm: () => {
        fetch(`${import.meta.env.VITE_API_URL}/chats/${chatId}`, { method: 'DELETE' })
          .then(() => {
            setChats(chats.filter(c => c.id !== chatId));
            setSelectedChat(null);
          })
          .catch(err => console.error("Failed to delete chat", err));
      }
    });
  };

  const handleCreateGroup = (newGroup) => {
    const groupWithCreator = {
      ...newGroup,
      participants: user ? [user] : [],
      members: 1,
      createdBy: user ? { name: user.name, email: user.email } : null
    };

    fetch('${import.meta.env.VITE_API_URL}/chats', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(groupWithCreator)
    })
      .then(res => res.json())
      .then(createdGroup => {
        setChats(prevChats => [createdGroup, ...prevChats]);
        setSelectedChat(createdGroup);
      })
      .catch(err => {
        console.error("Failed to create group", err);
        alert("Failed to create group. Please try again.");
      });
  };

  const handleJoinGroup = (group) => {
    if (!user) return;

    // Use the add_participant endpoint to add self
    fetch(`${import.meta.env.VITE_API_URL}/chats/${group.id}/participants`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: user.email })
    })
      .then(res => {
        if (!res.ok) throw new Error("Failed to join group");
        return res.json();
      })
      .then(() => {
        // Refresh chats to show the new group
        return fetch('${import.meta.env.VITE_API_URL}/chats');
      })
      .then(res => res.json())
      .then(data => {
        // Find joined chat
        const joinedChat = data.find(c => c.id === group.id);

        if (joinedChat) {
          // Mark as read immediately
          const updatedData = data.map(c => c.id === group.id ? { ...c, unread: 0 } : c);
          setChats(updatedData);
          setSelectedChat({ ...joinedChat, unread: 0 });
        } else {
          setChats(data);
        }
      })
      .catch(err => {
        console.error("Join group error", err);
        alert("Failed to join group");
      });
  };


  const handleUpdateProfile = (newName) => {
    if (!newName.trim()) return;

    fetch(`${import.meta.env.VITE_API_URL}/users/${user.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName })
    })
      .then(res => res.json())
      .then(updatedUser => {
        setUser(updatedUser);
      })
      .catch(err => console.error("Failed to update profile", err));
  };

  const renderMainContent = () => {
    switch (activeTab) {
      case 'chats':
        return selectedChat ? (
          <ChatWindow
            chat={selectedChat}
            chats={chats}
            userStatuses={userStatuses}
            currentUser={user}
            onBack={() => setSelectedChat(null)}
            onDeleteChat={handleDeleteChat}
          />
        ) : (
          <div className="hidden md:flex items-center justify-center h-full bg-[#f0f2f5] text-gray-500">
            Select a chat to start messaging
          </div>
        );
      case 'ideas':
        return <IdeaHub />;
      case 'calendar':
        return <CalendarView />;
      case 'profile':
        return (
          <Profile
            user={user}
            onUpdateProfile={handleUpdateProfile}
            onTabChange={setActiveTab}
            onLogout={() => setUser(null)}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      {/* Sidebar (Hidden on mobile if chat is selected, visible otherwise) */}
      <div className={`${selectedChat ? 'hidden md:flex' : 'flex'} w-full md:w-auto flex-col h-full`}>
        <Sidebar
          chats={chats}
          publicGroups={publicGroups}
          onSelectChat={handleSelectChat}
          onCreateGroup={handleCreateGroup}
          onJoinGroup={handleJoinGroup}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onLogout={() => setUser(null)}
        />
        <div className="md:hidden">
          <BottomNav activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
      </div>

      {/* Main Content Area */}
      <div className={`flex-1 h-full ${!selectedChat && activeTab === 'chats' ? 'hidden md:block' : 'block'}`}>
        {renderMainContent()}
      </div>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={confirmation.isOpen}
        onClose={() => setConfirmation({ ...confirmation, isOpen: false })}
        onConfirm={confirmation.onConfirm}
        title={confirmation.title}
        message={confirmation.message}
        isDanger={confirmation.isDanger}
        confirmText="Delete"
      />
    </div>
  );
};

export default Layout;
