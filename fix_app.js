const fs = require('fs');
let content = fs.readFileSync('mobile-judge-app/App.tsx', 'utf8');

content = content.replace(
\`							</View>
						)
					}
						</View>
					</View >
				);
}

// Render standard swimmer view
return (
	<TouchableOpacity
		style={[styles.swimmerCard, item.empty && styles.emptyCard]}
		onPress={() => handleDQ(item)}
	>
		<View style={[styles.laneCircle, item.empty && styles.emptyLane]}>
			<Text style={styles.laneText}>{item.lane}</Text>
		</View>
		<View style={styles.swimmerInfo}>
			<Text
				style={[styles.swimmerName, item.empty && styles.emptyText]}
			>
				{item.name}
			</Text>
			<Text style={styles.teamName}>{item.team}</Text>
			{item.notes ? (
				<Text style={styles.notePreview} numberOfLines={1}>
					{item.notes}
				</Text>
			) : null}
		</View>
		<Text
			style={[
				styles.dqTrigger,
				!item.dq_code && { color: COLORS.secondary },
			]}
		>
			{item.dq_code ? item.dq_code : "TAP TO DQ"}
		</Text>
	</TouchableOpacity>
);
		}}
	/>
</View >\`,
\`									</View>
								)}
							</View>
						);
					}

					// Render standard swimmer view
					return (
						<TouchableOpacity
							style={[styles.swimmerCard, item.empty && styles.emptyCard]}
							onPress={() => handleDQ(item)}
						>
							<View style={[styles.laneCircle, item.empty && styles.emptyLane]}>
								<Text style={styles.laneText}>{item.lane}</Text>
							</View>
							<View style={styles.swimmerInfo}>
								<Text
									style={[styles.swimmerName, item.empty && styles.emptyText]}
								>
									{item.name}
								</Text>
								<Text style={styles.teamName}>{item.team}</Text>
								{item.notes ? (
									<Text style={styles.notePreview} numberOfLines={1}>
										{item.notes}
									</Text>
								) : null}
							</View>
							<Text
								style={[
									styles.dqTrigger,
									!item.dq_code && { color: COLORS.secondary },
								]}
							>
								{item.dq_code ? item.dq_code : "TAP TO DQ"}
							</Text>
						</TouchableOpacity>
					);
				}}
			/>
		</View>\`
);

fs.writeFileSync('mobile-judge-app/App.tsx', content);
