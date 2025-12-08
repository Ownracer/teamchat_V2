import React, { useState, useEffect, useRef } from 'react';
import { Search, MoreVertical, MessageSquare, Lightbulb, Calendar, User, Plus, Users, Link as LinkIcon, Lock, Globe, LogOut, Star, CheckSquare, UserPlus, X, Trash2 } from 'lucide-react';

const Sidebar = ({ chats, publicGroups, onSelectChat, onCreateGroup, onJoinGroup, activeTab, onTabChange, onLogout, currentUser, onBulkDelete, showNotification }) => {
    const [searchQuery, setSearchQuery] = useState('');
    const [showCreateGroup, setShowCreateGroup] = useState(false);
    const [newGroupName, setNewGroupName] = useState('');
    const [isPrivate, setIsPrivate] = useState(true);
    const [showMenu, setShowMenu] = useState(false);
    const menuRef = useRef(null);

    // Selection Mode State
    const [isSelectionMode, setIsSelectionMode] = useState(false);
    const [selectedChatIds, setSelectedChatIds] = useState([]);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setShowMenu(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    const handleCreateGroup = () => {
        if (!newGroupName) return;
        const newGroup = {
            name: newGroupName,
            lastMessage: 'Group created',
            time: 'Just now',
            unread: 0,
            avatar: `https://ui-avatars.com/api/?name=${newGroupName}&background=random`,
            type: 'group',
            isPrivate: isPrivate
        };
        onCreateGroup(newGroup);
        setNewGroupName('');
        setShowCreateGroup(false);
    };

    const toggleChatSelection = (chatId) => {
        setSelectedChatIds(prev =>
            prev.includes(chatId) ? prev.filter(id => id !== chatId) : [...prev, chatId]
        );
    };

    const handleSelectChatsClick = () => {
        setIsSelectionMode(true);
        setShowMenu(false);
        setSelectedChatIds([]);
    };

    const handleStarredMessagesClick = () => {
        showNotification("Starred messages feature coming soon!");
        setShowMenu(false);
    };

    const filteredChats = chats.filter(chat =>
        chat.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const filteredPublicGroups = searchQuery && publicGroups ? publicGroups.filter(group =>
        group.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !chats.find(c => c.id === group.id) // Exclude if already joined
    ) : [];

    const renderContent = () => {
        switch (activeTab) {
            case 'chats':
                return (
                    <>
                        {/* Search */}
                        <div className="p-2">
                            <div className="bg-gray-100 rounded-lg flex items-center px-3 py-2">
                                <Search size={20} className="text-gray-500 mr-2" />
                                <input
                                    type="text"
                                    placeholder="Search chats or public groups..."
                                    className="bg-transparent focus:outline-none text-sm w-full"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                />
                            </div>
                        </div>

                        {/* Chat List */}
                        <div className="flex-1 overflow-y-auto">
                            {/* My Chats */}
                            {filteredChats.map((chat) => (
                                <div
                                    key={chat.id}
                                    onClick={() => isSelectionMode ? toggleChatSelection(chat.id) : onSelectChat(chat)}
                                    className={`flex items-center p-3 hover:bg-gray-50 cursor-pointer border-b border-gray-50 ${isSelectionMode && selectedChatIds.includes(chat.id) ? 'bg-teal-50' : ''}`}
                                >
                                    {isSelectionMode && (
                                        <div className={`w-5 h-5 rounded border mr-3 flex items-center justify-center ${selectedChatIds.includes(chat.id) ? 'bg-teal-500 border-teal-500' : 'border-gray-400'}`}>
                                            {selectedChatIds.includes(chat.id) && <CheckSquare size={14} className="text-white" />}
                                        </div>
                                    )}
                                    <img src={chat.avatar} alt={chat.name} className="w-12 h-12 rounded-full mr-3" />
                                    <div className="flex-1 min-w-0">
                                        <div className="flex justify-between items-baseline">
                                            <h3 className="font-semibold text-gray-800 truncate flex items-center">
                                                {chat.name}
                                                {chat.type === 'group' && (
                                                    <span className="ml-1 text-gray-400">
                                                        {chat.isPrivate ? <Lock size={12} /> : <Globe size={12} />}
                                                    </span>
                                                )}
                                            </h3>
                                            <span className="text-xs text-gray-500">{chat.time}</span>
                                        </div>
                                        <div className="flex justify-between items-center mt-1">
                                            <p className="text-sm text-gray-600 truncate">{chat.lastMessage}</p>
                                            {chat.unread > 0 && (
                                                <span className="bg-teal-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
                                                    {chat.unread}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}

                            {/* Public Groups Search Results */}
                            {filteredPublicGroups.length > 0 && (
                                <>
                                    <div className="px-4 py-2 bg-gray-50 text-xs font-bold text-gray-500 uppercase tracking-wider">
                                        Public Groups to Join
                                    </div>
                                    {filteredPublicGroups.map((group) => (
                                        <div key={group.id} className="flex items-center p-3 hover:bg-gray-50 border-b border-gray-50">
                                            <img src={group.avatar} alt={group.name} className="w-12 h-12 rounded-full mr-3" />
                                            <div className="flex-1 min-w-0">
                                                <div className="flex justify-between items-baseline">
                                                    <h3 className="font-semibold text-gray-800 truncate flex items-center">
                                                        {group.name}
                                                        <span className="ml-1 text-gray-400"><Globe size={12} /></span>
                                                    </h3>
                                                </div>
                                                <p className="text-sm text-gray-600 truncate">{group.description}</p>
                                                <p className="text-xs text-gray-400 mt-1">{group.members} members</p>
                                            </div>
                                            <button
                                                onClick={() => onJoinGroup(group)}
                                                className="ml-2 px-3 py-1 bg-teal-50 text-teal-600 text-xs font-bold rounded-full hover:bg-teal-100"
                                            >
                                                Join
                                            </button>
                                        </div>
                                    ))}
                                </>
                            )}

                            {searchQuery && filteredChats.length === 0 && filteredPublicGroups.length === 0 && (
                                <div className="p-4 text-center text-gray-500 text-sm">
                                    No chats or public groups found.
                                </div>
                            )}
                        </div>

                        {/* Create Group Modal Overlay */}
                        {showCreateGroup && (
                            <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                                <div className="bg-white rounded-xl p-6 w-full max-w-sm shadow-2xl">
                                    <h3 className="text-lg font-bold mb-4 text-gray-800">Create New Group</h3>
                                    <input
                                        type="text"
                                        placeholder="Group Name"
                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:border-teal-500"
                                        value={newGroupName}
                                        onChange={(e) => setNewGroupName(e.target.value)}
                                    />
                                    <div className="flex items-center justify-between mb-6">
                                        <span className="text-sm text-gray-600 font-medium">Group Type</span>
                                        <div className="flex bg-gray-100 rounded-lg p-1">
                                            <button
                                                onClick={() => setIsPrivate(true)}
                                                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${isPrivate ? 'bg-white shadow-sm text-teal-600' : 'text-gray-500'}`}
                                            >
                                                Private
                                            </button>
                                            <button
                                                onClick={() => setIsPrivate(false)}
                                                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${!isPrivate ? 'bg-white shadow-sm text-teal-600' : 'text-gray-500'}`}
                                            >
                                                Public
                                            </button>
                                        </div>
                                    </div>
                                    <div className="flex space-x-2">
                                        <button onClick={() => setShowCreateGroup(false)} className="flex-1 py-2 text-gray-500 hover:bg-gray-100 rounded-lg">Cancel</button>
                                        <button onClick={handleCreateGroup} className="flex-1 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700">Create</button>
                                    </div>
                                </div>
                            </div>
                        )}
                    </>
                );
            case 'ideas':
                return <div className="p-4 text-center text-gray-500">Select an idea from the hub to view details</div>;
            case 'calendar':
                return <div className="p-4 text-center text-gray-500">Calendar events list</div>;
            case 'profile':
                return (
                    <div className="p-6 flex flex-col items-center">
                        <div className="w-24 h-24 rounded-full mb-4 bg-orange-500 flex items-center justify-center text-4xl text-white font-bold">
                            {currentUser?.name?.charAt(0).toUpperCase()}
                        </div>
                        <h2 className="text-xl font-bold text-gray-800">{currentUser?.name || "User"}</h2>
                        <p className="text-gray-500">{currentUser?.email}</p>
                        <p className="text-gray-400 text-sm mt-1">Online</p>
                        <button onClick={onLogout} className="mt-6 w-full bg-red-50 text-red-600 py-2 rounded-lg hover:bg-red-100">
                            Logout
                        </button>
                    </div>
                );
            default:
                return null;
        }
    };

    return (
        <div className="w-full md:w-[400px] bg-white border-r border-gray-200 flex flex-col h-full relative">
            {/* Header */}
            <div className="h-16 bg-gray-50 px-4 flex items-center justify-between border-b border-gray-200">
                {isSelectionMode ? (
                    <div className="flex items-center justify-between w-full">
                        <div className="flex items-center space-x-2">
                            <button onClick={() => setIsSelectionMode(false)} className="p-2 hover:bg-gray-200 rounded-full">
                                <X size={20} className="text-gray-600" />
                            </button>
                            <span className="font-bold text-gray-700">{selectedChatIds.length} selected</span>
                        </div>
                        {selectedChatIds.length > 0 && (
                            <button
                                onClick={() => { onBulkDelete(selectedChatIds); setIsSelectionMode(false); }}
                                className="p-2 hover:bg-red-100 text-red-600 rounded-full"
                                title="Delete selected"
                            >
                                <Trash2 size={20} />
                            </button>
                        )}
                    </div>
                ) : (
                    <>
                        <div className="flex items-center space-x-2">
                            <div
                                className="w-8 h-8 rounded-full bg-orange-500 flex items-center justify-center text-white text-xs font-bold cursor-pointer hover:opacity-90 transition-opacity"
                                onClick={() => onTabChange('profile')}
                            >
                                {currentUser?.name?.charAt(0).toUpperCase()}
                            </div>
                            <h1 className="font-bold text-gray-700">Teamchat</h1>
                        </div>
                        <div className="flex space-x-2 relative" ref={menuRef}>
                            <button
                                onClick={() => setShowMenu(!showMenu)}
                                className={`p-2 rounded-full transition-colors ${showMenu ? 'bg-gray-200' : 'hover:bg-gray-100'}`}
                            >
                                <MoreVertical size={20} />
                            </button>

                            {/* Dropdown Menu */}
                            {showMenu && (
                                <div className="absolute right-0 top-10 w-48 bg-[#202c33] text-gray-300 rounded-lg shadow-xl z-50 py-2 border border-gray-700">
                                    <button
                                        onClick={() => { setShowCreateGroup(true); setShowMenu(false); }}
                                        className="w-full text-left px-4 py-3 hover:bg-[#111b21] flex items-center space-x-3 transition-colors"
                                    >
                                        <UserPlus size={18} />
                                        <span>New group</span>
                                    </button>
                                    <button
                                        onClick={handleStarredMessagesClick}
                                        className="w-full text-left px-4 py-3 hover:bg-[#111b21] flex items-center space-x-3 transition-colors"
                                    >
                                        <Star size={18} />
                                        <span>Starred messages</span>
                                    </button>
                                    <button
                                        onClick={handleSelectChatsClick}
                                        className="w-full text-left px-4 py-3 hover:bg-[#111b21] flex items-center space-x-3 transition-colors"
                                    >
                                        <CheckSquare size={18} />
                                        <span>Select chats</span>
                                    </button>
                                    <div className="h-px bg-gray-700 my-1"></div>
                                    <button
                                        onClick={() => { if (onLogout) onLogout(); setShowMenu(false); }}
                                        className="w-full text-left px-4 py-3 hover:bg-[#111b21] flex items-center space-x-3 transition-colors text-red-400"
                                    >
                                        <LogOut size={18} />
                                        <span>Log out</span>
                                    </button>
                                </div>
                            )}
                        </div>
                    </>
                )}
            </div>

            {/* Tabs */}
            <div className="flex justify-around bg-white border-b border-gray-200">
                <button
                    onClick={() => onTabChange('chats')}
                    className={`flex-1 py-3 flex justify-center items-center ${activeTab === 'chats' ? 'border-b-2 border-teal-500 text-teal-600' : 'text-gray-500 hover:bg-gray-50'}`}
                >
                    <MessageSquare size={20} />
                </button>
                <button
                    onClick={() => onTabChange('ideas')}
                    className={`flex-1 py-3 flex justify-center items-center ${activeTab === 'ideas' ? 'border-b-2 border-teal-500 text-teal-600' : 'text-gray-500 hover:bg-gray-50'}`}
                >
                    <Lightbulb size={20} />
                </button>
                <button
                    onClick={() => onTabChange('calendar')}
                    className={`flex-1 py-3 flex justify-center items-center ${activeTab === 'calendar' ? 'border-b-2 border-teal-500 text-teal-600' : 'text-gray-500 hover:bg-gray-50'}`}
                >
                    <Calendar size={20} />
                </button>
                <button
                    onClick={() => onTabChange('profile')}
                    className={`flex-1 py-3 flex justify-center items-center ${activeTab === 'profile' ? 'border-b-2 border-teal-500 text-teal-600' : 'text-gray-500 hover:bg-gray-50'}`}
                >
                    <User size={20} />
                </button>
            </div>

            {renderContent()}
        </div>
    );
};

export default Sidebar;
