import { Messages } from './comps/Messages';
import { Search } from './comps/Search';
import { useState, useEffect } from 'react';
import io from 'socket.io-client';

const socket = io('http://127.0.0.1:5000');

function App() {
	const [messages, setMessages] = useState([]);
	const [inMediation, setInMediation] = useState(false);
	const [userType, setUserType] = useState('');
	const [opportunityCost, setOpportunityCost] = useState('');

	useEffect(() => {
		const handleMessage = (data) => {
			if (data.message?.includes('Defendant questions completed.')) {
				if (userType === 'defendant') {
					setMessages((prevMessages) => [
						...prevMessages,
						{ author: data.author, message: data.message },
					]);
				}

				if (userType === 'plaintiff') {
					setMessages((prevMessages) => [
						...prevMessages,
						{
							author: data.author,
							message:
								'The mediation between both parties will start in a moment.',
						},
					]);
				}

				setTimeout(() => {
					setInMediation(true);
					setMessages([]);
				}, 1000);

				return;
			}

			setMessages((prevMessages) => [
				...prevMessages,
				{ author: data.author, message: data.message },
			]);
		};

		const handleQuestion = (data) => {
			setMessages((prevMessages) => [
				...prevMessages,
				{ author: 'Mediator', message: data.next_question },
			]);
		};

		const handleAIResponse = (data) => {
			setMessages((prevMessages) => [
				...prevMessages,
				{ author: 'AI Mediator', message: data.ai_response },
			]);

			if ('opportunityCost' in data) {
				setOpportunityCost(data.opportunityCost);
			}
		};

		socket.on('message', handleMessage);
		socket.on('ai_response', handleAIResponse);
		socket.on('next_question', handleQuestion);

		return () => {
			socket.off('message', handleMessage);
			socket.off('ai_response', handleAIResponse);
			socket.off('next_question', handleQuestion);
			socket.disconnect();
		};
	}, [userType]);

	useEffect(() => {
		if (userType) {
			socket.emit('register_user', {
				user_type: userType,
				name: userType === 'plaintiff' ? 'joe' : 'don',
			});

			if (userType === 'plaintiff') {
				setMessages([
					{
						author: 'Mediator',
						message: 'What kind of dispute are you resolving?',
					},
				]);
			}

			// if (userType === 'defendant')
			// 	socket.emit('initial_questions', {
			// 		user_type: userType,
			// 		answer: '',
			// 	});
		}
	}, [userType]);

	const submitAnswer = (text) => {
		if (inMediation) {
			socket.emit('mediate', {
				plaintiff_name: 'Joe',
				defendant_name: 'Defendant',
				user_input: text,
			});
			setMessages((prevMessages) => [
				...prevMessages,
				{ author: userType === 'plaintiff' ? 'joe' : 'don', message: text },
			]);
		} else {
			socket.emit('initial_questions', {
				user_type: userType,
				answer: text,
			});
			setMessages((prevMessages) => [
				...prevMessages,
				{ author: userType === 'plaintiff' ? 'joe' : 'don', message: text },
			]);
		}
	};

	return (
		<div className="w-full h-screen bg-slate-200 flex justify-center items-center">
			{userType ? (
				<div className="w-1/2 h-5/6 flex flex-col gap-2">
					<div className="text-3xl font-bold self-start">Dispute Mediation</div>
					<Messages messages={messages} />
					<Search submit={submitAnswer} />
				</div>
			) : (
				<div className="flex flex-col gap-4 items-center justify-center">
					<div className="flex items-center justify-center w-full gap-2">
						<div className="font-bold">Are you the plaintiff?</div>
						<div className="flex gap-2">
							<input
								type="radio"
								value="plaintiff"
								name="userType"
								checked={userType === 'plaintiff'}
								onChange={(e) => setUserType(e.target.value)}
							/>{' '}
							Yes
							<input
								type="radio"
								value="defendant"
								name="userType"
								checked={userType === 'defendant'}
								onChange={(e) => setUserType(e.target.value)}
							/>{' '}
							No
						</div>
					</div>
				</div>
			)}
		</div>
	);
}

export default App;
