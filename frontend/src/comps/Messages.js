import { Message } from './Message';

export const Messages = ({ messages }) => {
	return (
		<div className="p-3 px-4 bg-white border-black border-[.5px] shadow overflow-y-scroll rounded-lg h-full w-full flex flex-col gap-3">
			{messages.map((message, index) => (
				<Message
					content={message.message}
					key={index}
					// author={message.author}
				/>
			))}
		</div>
	);
};
