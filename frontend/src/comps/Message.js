export const Message = ({ content, author }) => {
	return (
		<div className={`flex flex-col ${author === 'self' && 'self-end'}`}>
			<div className={`text-base font-bold ${author === 'self' && 'self-end'}`}>
				{author === 'self' ? '' : author}
			</div>
			<div
				className={`${
					author === 'self' ? 'bg-sky-300' : 'bg-amber-300'
				} max-w-lg w-fit h-fit p-3 rounded-lg`}
			>
				{content}
			</div>
		</div>
	);
};
