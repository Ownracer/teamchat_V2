import React, { useEffect, useState } from 'react';
import { Filter, Plus, Trash2 } from 'lucide-react';

const IdeaHub = () => {
    const [ideas, setIdeas] = useState([]);

    useEffect(() => {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        fetch(`${apiUrl}/ideas`)
            .then(res => res.json())
            .then(data => {
                setIdeas(data);
            })
            .catch(err => console.error("Failed to fetch ideas", err));
    }, []);

    const handleDeleteIdea = (id) => {
        if (window.confirm("Are you sure you want to delete this idea?")) {
            fetch(`${import.meta.env.VITE_API_URL}/ideas/${id}`, { method: 'DELETE' })
                .then(() => {
                    setIdeas(ideas.filter(idea => idea.id !== id));
                })
                .catch(err => console.error("Failed to delete idea", err));
        }
    };

    const [selectedIdea, setSelectedIdea] = useState(null);
    const [suggestionExpanded, setSuggestionExpanded] = useState(false);

    const openIdeaModal = (idea) => {
        setSelectedIdea(idea);
        setSuggestionExpanded(false); // Reset to collapsed
    };

    return (
        <div className="flex flex-col h-full bg-gray-50 p-4 relative">
            {/* ... (Header and Filters remain same) ... */}
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold text-gray-800">Idea Hub 💡</h1>
                <button className="bg-teal-500 text-white px-4 py-2 rounded-lg flex items-center space-x-2 hover:bg-teal-600">
                    <Plus size={20} />
                    <span>New Idea</span>
                </button>
            </div>

            {/* Filters */}
            <div className="flex space-x-2 mb-6 overflow-x-auto pb-2">
                {['All', 'Campaign', 'Blog', 'Event', 'Dev', 'Document'].map((filter) => (
                    <button key={filter} className="px-4 py-1.5 bg-white border border-gray-200 rounded-full text-sm font-medium text-gray-600 hover:bg-gray-50 whitespace-nowrap">
                        {filter}
                    </button>
                ))}
                <button className="px-2 py-1.5 bg-gray-100 rounded-full text-gray-500">
                    <Filter size={18} />
                </button>
            </div>

            {/* Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 overflow-y-auto">
                {ideas.map((idea) => (
                    <div
                        key={idea.id}
                        onClick={() => openIdeaModal(idea)}
                        className={`${idea.color} p-4 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between h-48 cursor-pointer hover:shadow-md transition-shadow relative group`}
                    >
                        <button
                            onClick={(e) => { e.stopPropagation(); handleDeleteIdea(idea.id); }}
                            className="absolute top-2 right-2 p-1.5 bg-white bg-opacity-50 rounded-full text-red-500 opacity-0 group-hover:opacity-100 hover:bg-white transition-all"
                            title="Delete Idea"
                        >
                            <Trash2 size={16} />
                        </button>
                        <div>
                            <div className="flex justify-between items-start mb-2">
                                <span className="text-xs font-bold uppercase tracking-wider opacity-70">{idea.category}</span>
                                <span className={`text-xs px-2 py-1 rounded-full bg-white bg-opacity-50 font-medium`}>{idea.priority}</span>
                            </div>
                            <h3 className="text-lg font-bold text-gray-800 leading-tight">{idea.title}</h3>
                            {idea.suggestion && (
                                <p className="text-xs text-gray-600 mt-2 line-clamp-3 bg-gray-50 p-2 rounded">
                                    {idea.suggestion}
                                </p>
                            )}
                        </div>
                        <div className="flex justify-between items-center mt-4">
                            <span className="text-sm font-medium text-gray-700">{idea.status}</span>
                            <div className="flex -space-x-2">
                                <img src={`https://ui-avatars.com/api/?name=User+${idea.id}&background=random`} className="w-6 h-6 rounded-full border-2 border-white" alt="User" />
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Idea Details Modal */}
            {selectedIdea && (
                <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={() => setSelectedIdea(null)}>
                    <div className="bg-white rounded-xl w-full max-w-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden" onClick={e => e.stopPropagation()}>
                        <div className={`p-6 ${selectedIdea.color} flex justify-between items-start`}>
                            <div>
                                <span className="text-xs font-bold uppercase tracking-wider opacity-70 mb-2 block">{selectedIdea.category}</span>
                                <h2 className="text-2xl font-bold text-gray-900">{selectedIdea.title}</h2>
                            </div>
                            <button onClick={() => setSelectedIdea(null)} className="p-2 bg-white bg-opacity-50 rounded-full hover:bg-opacity-100 transition-all">
                                <Trash2 size={20} className="text-gray-600" />
                            </button>
                        </div>
                        <div className="p-6 overflow-y-auto">
                            <div className="grid grid-cols-2 gap-4 mb-6">
                                <div className="bg-gray-50 p-3 rounded-lg">
                                    <p className="text-xs text-gray-500 uppercase">Status</p>
                                    <p className="font-medium text-gray-800">{selectedIdea.status}</p>
                                </div>
                                <div className="bg-gray-50 p-3 rounded-lg">
                                    <p className="text-xs text-gray-500 uppercase">Priority</p>
                                    <p className="font-medium text-gray-800">{selectedIdea.priority}</p>
                                </div>
                                <div className="bg-gray-50 p-3 rounded-lg">
                                    <p className="text-xs text-gray-500 uppercase">Deadline</p>
                                    <p className="font-medium text-gray-800">{selectedIdea.deadline || 'None'}</p>
                                </div>
                            </div>

                            <div className="mb-6">
                                <h3 className="text-lg font-semibold text-gray-800 mb-2">Suggestion / Analysis</h3>
                                <div
                                    className={`bg-blue-50 rounded-lg border border-blue-100 text-gray-700 cursor-pointer hover:bg-blue-100 transition-colors overflow-hidden ${suggestionExpanded ? '' : 'max-h-16'}`}
                                    onClick={() => setSuggestionExpanded(!suggestionExpanded)}
                                >
                                    <div className="p-4">
                                        <p className={`leading-relaxed ${suggestionExpanded ? '' : 'line-clamp-2'}`}>
                                            {selectedIdea.suggestion || "No detailed analysis available."}
                                        </p>
                                        {!suggestionExpanded && (
                                            <p className="text-xs text-blue-500 mt-1 font-medium text-center">Tap to expand</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end">
                            <button onClick={() => setSelectedIdea(null)} className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 font-medium">
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default IdeaHub;
