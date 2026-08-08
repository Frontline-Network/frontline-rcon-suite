import { Avatar, Chip } from "@mui/material";
import PublicIcon from "@mui/icons-material/Public";
import React from "react";
import { useEditAccountModal } from "@/hooks/useEditAccountModal";
import { CountryFlag } from "@/components/shared/CountryFlag";

function CountryChip({ country, playerId, currentAccountData }) {
  const { modal, openModal } = useEditAccountModal(
    playerId,
    currentAccountData
  );

  return (
    <>
      {country && country !== "private" ? (
        <Chip
          avatar={
            <Avatar sx={{ bgcolor: "transparent" }}>
              <CountryFlag country={country} />
            </Avatar>
          }
          label={country}
          variant="outlined"
          size="small"
          onClick={openModal}
        />
      ) : (
        <Chip
          icon={<PublicIcon />}
          label="unset"
          variant="outlined"
          size="small"
          onClick={openModal}
        />
      )}
      {modal}
    </>
  );
}

export default CountryChip;
