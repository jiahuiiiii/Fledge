import Card from "./Card";
import SectionHeader from "./SectionHeader";

export default function EmptyState({
  title,
  description,
  icon,
  actions,
  className = "",
  ...rest
}) {
  return (
    <Card className={`ui-empty-state ${className}`} {...rest}>
      <SectionHeader
        level="section"
        as="h3"
        icon={icon}
        title={title}
        description={description}
      />
      {actions && <div className="ui-empty-state__actions">{actions}</div>}
    </Card>
  );
}
