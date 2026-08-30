import PlayerFlagPicker from "./PlayerFlagPicker";

export default function NameKickFlagsField(props) {
  return (
    <PlayerFlagPicker
      {...props}
      translationRoot="settings.configForms.nameKicks.flagPicker"
    />
  );
}
