import { CommentField } from "../fields/CommentField"
import { useTranslation } from "react-i18next";

export const AddCommentFormFields = (props) => {
    const { t } = useTranslation();
    return (
        <CommentField rules={{ required: t("fields.commentRequired") }} {...props} />
    )
}
