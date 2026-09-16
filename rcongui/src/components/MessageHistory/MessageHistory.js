import {Box, Chip} from "@mui/material";
import Typography from "@mui/material/Typography";
import moment from "moment";
import "moment/locale/de";
import Grid from "@mui/material/Grid2";
import { useTranslation } from "react-i18next";

const MessageHistory = ({data}) => {
  const { t, i18n } = useTranslation();
  return (<Box paddingLeft={2}>
    <Grid
      container
      justifyContent="flex-start"
      alignContent="flex-start"
      alignItems="flex-end"
      direction="column"
      wrap="nowrap"
    >
      {data?.map((message, index) => {
        return (
          (<Grid key={index}>
            <Grid
              container
              justifyContent="flex-start"
              alignContent="flex-start"
              alignItems="flex-end"
              direction="column"
            >
              <Grid>
                <Chip
                  style={{height: "auto", paddingTop: "-10px"}}
                  color="primary"
                  label={
                    <Typography align="left">
                      {message.reason}
                    </Typography>
                  }/>
              </Grid>
              <Grid>
                <Typography
                  variant="caption"
                  display="block"

                  color="textSecondary"
                >
                  {moment
                    .utc(message.time)
                    .local()
                    .locale(i18n.resolvedLanguage)
                    .format(t("common.logDateTimeFormat"))}{" "}
                  {t("sharedOperations.by", { name: message.by })}
                </Typography>
              </Grid>
            </Grid>
          </Grid>)
        );
      })}
    </Grid>
  </Box>);
};

export default MessageHistory;
