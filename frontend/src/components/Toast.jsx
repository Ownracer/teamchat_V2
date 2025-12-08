import React, { useEffect } from 'react';
import { X } from 'lucide-react';

const Toast = ({ message, onClose }) => {
    useEffect(() => {
        const timer = setTimeout(() => {
            onClose();
        }, 3000);
        return () => clearTimeout(timer);
    }, [onClose]);

    if (!message) return null;

    return (
        <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 z-50 animate-fade-in-up">
            <span>{message}</span>
            <button onClick={onClose} className="p-1 hover:bg-gray-700 rounded-full">
                <X size={14} />
            </button>
        </div>
    );
};

export default Toast;
