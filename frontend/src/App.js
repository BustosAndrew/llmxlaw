import { Messages } from './comps/Messages';
import { Search } from './comps/Search';
import { useState, useEffect } from 'react';
import io from 'socket.io-client';

const socket = io('http://localhost:5000');

function App() {
	const [title, setTitle] = useState('Dispute');
	const [messages, setMessages] = useState([]);

	useEffect(() => {
		// Listen for incoming messages
		socket.on('message', (message) => {
			setMessages((prevMessages) => [...prevMessages, message]);
		});

		// Fetch initial messages when the component mounts
		fetchMessages();

		// Clean up the socket connection on unmount
		return () => {
			socket.off('message');
		};
	}, []);

	const fetchMessages = async () => {
		try {
			const response = await fetch('http://localhost:5000/messages');
			const data = await response.json();
			setMessages(data);
		} catch (error) {
			console.error('Error fetching messages:', error);
		}
	};

	const submit = (text) => {
		// Emit the message to the server
		socket.emit('sendMessage', { text });
	};

	return (
		<div className="w-full h-screen bg-slate-200 flex justify-center items-center">
			<div className="w-1/2 h-5/6 flex flex-col gap-2">
				<div className="text-3xl font-bold self-start">{title}</div>
				<Messages messages={messages} />
				<Search submit={submit} />
			</div>
		</div>
	);
}

export default App;
