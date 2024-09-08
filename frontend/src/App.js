import { Messages } from './comps/Messages';
import { Search } from './comps/Search';
import { useState, useEffect } from 'react';
import io from 'socket.io-client';

const socket = io('http://localhost:5000');

function App() {
	const [title, setTitle] = useState('Dispute Mediation');
	const [messages, setMessages] = useState([]);
	const [userType, setUserType] = useState('');
	const [currentQuestion, setCurrentQuestion] = useState('');
	const [mediationStarted, setMediationStarted] = useState(false);
	const [nextUser, setNextUser] = useState('');

	useEffect(() => {
		socket.on('response', (data) => {
			setMessages((prevMessages) => [...prevMessages, data.message]);
		});

		socket.on('next_question', (data) => {
			setCurrentQuestion(data.next_question);
		});

		socket.on('message', (data) => {
			setMessages((prevMessages) => [...prevMessages, data.message]);
			if (data.message.includes('Mediation ready to start')) {
				setMediationStarted(true);
			}
		});

		socket.on('ai_response', (data) => {
			setMessages((prevMessages) => [...prevMessages, data.ai_response]);
			setNextUser(data.next_user);
		});

		return () => {
			socket.off('response');
			socket.off('next_question');
			socket.off('message');
			socket.off('ai_response');
		};
	}, []);

	const registerUser = (type) => {
		setUserType(type);
		socket.emit('register_user', { user_type: type });
		socket.emit('initial_questions', { user_type: type });
	};

	const submitAnswer = (text) => {
		if (!mediationStarted) {
			socket.emit('initial_questions', { user_type: userType, answer: text });
		} else {
			socket.emit('mediate', {
				plaintiff_name: 'Plaintiff',
				defendant_name: 'Defendant',
				user_input: text,
			});
		}
	};

	return (
		<div className="w-full h-screen bg-slate-200 flex justify-center items-center">
			<div className="w-1/2 h-5/6 flex flex-col gap-2">
				<div className="text-3xl font-bold self-start">{title}</div>
				<Messages messages={messages} />
				<Search submit={submitAnswer} />
			</div>
		</div>
	);
}

export default App;
