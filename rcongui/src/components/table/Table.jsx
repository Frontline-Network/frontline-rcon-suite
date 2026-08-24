import { Fragment, useLayoutEffect, useRef, useState } from "react";
import { flexRender } from "@tanstack/react-table";
import { NoRowsOverlay } from "@/components/NoRowsOverlay";
import {
  StyledTable,
  StyledTd,
  StyledTh,
  StyledThead,
  StyledTr,
} from "./styles";
import { Box, LinearProgress } from "@mui/material";
import LoadingOverlay from "./LoadingOverlay";

const Table = ({
  table,
  config = {},
  renderSubComponent,
  rowProps = () => ({}),
  isLoading,
  isFetching,
  showTopScrollbar = false,
  topScrollbarLabel = "Scroll table columns horizontally",
}) => {
  const tableViewportRef = useRef(null);
  const topScrollbarRef = useRef(null);
  const [scrollWidth, setScrollWidth] = useState(0);
  const [viewportWidth, setViewportWidth] = useState(0);

  useLayoutEffect(() => {
    if (!showTopScrollbar) return undefined;

    const tableViewport = tableViewportRef.current;
    const topScrollbar = topScrollbarRef.current;
    if (!tableViewport || !topScrollbar) return undefined;

    const updateMetrics = () => {
      setScrollWidth(tableViewport.scrollWidth);
      setViewportWidth(tableViewport.clientWidth);
    };
    const syncFromTop = () => {
      tableViewport.scrollLeft = topScrollbar.scrollLeft;
    };
    const syncFromTable = () => {
      topScrollbar.scrollLeft = tableViewport.scrollLeft;
    };

    updateMetrics();
    topScrollbar.addEventListener("scroll", syncFromTop, { passive: true });
    tableViewport.addEventListener("scroll", syncFromTable, { passive: true });

    const resizeObserver =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(updateMetrics);
    resizeObserver?.observe(tableViewport);
    const renderedTable = tableViewport.querySelector("table");
    if (renderedTable) resizeObserver?.observe(renderedTable);
    window.addEventListener("resize", updateMetrics);

    return () => {
      topScrollbar.removeEventListener("scroll", syncFromTop);
      tableViewport.removeEventListener("scroll", syncFromTable);
      resizeObserver?.disconnect();
      window.removeEventListener("resize", updateMetrics);
    };
  }, [showTopScrollbar, table.getVisibleLeafColumns().length]);

  const hasHorizontalOverflow = scrollWidth > viewportWidth + 1;

  return (
    <>
      {showTopScrollbar ? (
        <Box
          ref={topScrollbarRef}
          role="region"
          aria-label={topScrollbarLabel}
          tabIndex={hasHorizontalOverflow ? 0 : -1}
          sx={{
            borderBottom: hasHorizontalOverflow ? "1px solid" : 0,
            borderColor: "divider",
            display: hasHorizontalOverflow ? "block" : "none",
            height: 13,
            overflowX: "auto",
            overflowY: "hidden",
            scrollbarWidth: "thin",
            width: "100%",
          }}
        >
          <Box sx={{ height: 1, width: scrollWidth }} />
        </Box>
      ) : null}
      <Box
        ref={tableViewportRef}
        sx={{
          overflowX: "auto",
          overflowY: "hidden",
          width: "100%",
          scrollbarWidth: "thin",
          position: "relative",
          marginTop: "2px",
        }}
      >
        {isFetching && (
          <LinearProgress
            sx={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "2px",
            }}
          />
        )}
        <StyledTable
          density={config.density}
          fontSize={config.fontSize}
          data-expanded-view={String(config.expandedView)}
        >
          <StyledThead>
            {table.getHeaderGroups().map((headerGroup) => (
              <StyledTr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <StyledTh
                      key={header.id}
                      variant={header.column.columnDef?.meta?.variant}
                      sticky={header.column.columnDef?.meta?.sticky}
                      stickyOffset={header.column.columnDef?.meta?.stickyOffset}
                    >
                      {header.isPlaceholder ? null : (
                        <div>
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                        </div>
                      )}
                    </StyledTh>
                  );
                })}
              </StyledTr>
            ))}
          </StyledThead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <Fragment key={row.id}>
                <StyledTr {...rowProps(row)}>
                  {row.getVisibleCells().map((cell) => (
                    <StyledTd
                      key={cell.id}
                      variant={cell.column.columnDef?.meta?.variant}
                      sticky={cell.column.columnDef?.meta?.sticky}
                      stickyOffset={cell.column.columnDef?.meta?.stickyOffset}
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </StyledTd>
                  ))}
                </StyledTr>
                {row.getIsExpanded() && renderSubComponent && (
                  <StyledTr>
                    {/* 2nd row is a custom 1 cell row */}
                    <StyledTd colSpan={row.getVisibleCells().length}>
                      {renderSubComponent({ row })}
                    </StyledTd>
                  </StyledTr>
                )}
              </Fragment>
            ))}
          </tbody>
        </StyledTable>
        {isLoading && <LoadingOverlay />}
        {!isLoading && table.getRowModel().rows.length === 0 && (
          <NoRowsOverlay />
        )}
      </Box>
    </>
  );
};

export default Table;
