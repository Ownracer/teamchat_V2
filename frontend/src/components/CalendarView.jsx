import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const CalendarView = () => {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const currentMonth = 'December 2025';
    const [events, setEvents] = useState([]);

    useEffect(() => {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        fetch(`${apiUrl}/ideas`)
            .then(res => res.json())
            .then(data => {
                // Filter ideas with deadlines and map to events
                const mappedEvents = data
                    .filter(idea => idea.deadline)
                    .map(idea => {
                        const date = new Date(idea.deadline);
                        return {
                            date: date.getDate(),
                            title: `${getCategoryEmoji(idea.category)} ${idea.title}`,
                            color: idea.color || 'bg-blue-200'
                        };
                    });

                setEvents(mappedEvents);
            })
            .catch(err => console.error("Failed to fetch ideas for calendar", err));
    }, []);

    const getCategoryEmoji = (category) => {
        switch (category) {
            case 'Campaign': return '🚀';
            case 'Blog': return '📝';
            case 'Event': return '📅';
            case 'Dev': return '💻';
            default: return '💡';
        }
    };

    const renderCalendarDays = () => {
        const calendarDays = [];
        // Simple logic for demo: assume month starts on Monday (index 1) and has 31 days
        for (let i = 0; i < 1; i++) {
            calendarDays.push(<div key={`empty-${i}`} className="h-24 bg-gray-50 border border-gray-100"></div>);
        }
        for (let i = 1; i <= 31; i++) {
            // Find all events for this day
            const dayEvents = events.filter(e => e.date === i);

            calendarDays.push(
                <div key={i} className="h-24 bg-white border border-gray-100 p-2 flex flex-col relative hover:bg-gray-50 overflow-hidden">
                    <span className={`text-sm font-medium ${dayEvents.length > 0 ? 'text-teal-600' : 'text-gray-700'}`}>{i}</span>
                    {dayEvents.map((event, idx) => (
                        <div key={idx} className={`mt-1 p-1 rounded text-[10px] truncate ${event.color} text-gray-800 font-medium`}>
                            {event.title}
                        </div>
                    ))}
                </div>
            );
        }
        return calendarDays;
    };

    return (
        <div className="flex flex-col h-full bg-white p-4">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold text-gray-800">Smart Calendar 📅</h1>
                <div className="flex items-center space-x-4">
                    <button className="p-1 hover:bg-gray-100 rounded-full"><ChevronLeft size={20} /></button>
                    <span className="font-semibold text-lg">{currentMonth}</span>
                    <button className="p-1 hover:bg-gray-100 rounded-full"><ChevronRight size={20} /></button>
                </div>
            </div>

            <div className="grid grid-cols-7 mb-2">
                {days.map(day => (
                    <div key={day} className="text-center text-sm font-medium text-gray-500 py-2">
                        {day}
                    </div>
                ))}
            </div>

            <div className="grid grid-cols-7 flex-1 overflow-y-auto border-t border-gray-200">
                {renderCalendarDays()}
            </div>
        </div>
    );
};

export default CalendarView;
