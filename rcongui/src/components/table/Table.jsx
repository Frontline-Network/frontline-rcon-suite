import { Fragment, memo, useLayoutEffect, useRef, useState } from "react";
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

const EMPTY_ROW_PROPS = () => ({});

const hasSameTableState = (previous = {}, next = {}) => {
  const keys = new Set([...Object.keys(previous), ...Object.keys(next)]);
  for (const key of keys) {
    if (previous[key] !== next[key]) return false;
  }
  return true;
};

const MemoizedTableBody = memo(
  function MemoizedTableBody({ rows, rowProps, renderSubComponent }) {
    return (
      <tbody>
        {rows.map((row) => (
          <Fragment key={row.id}>
            <StyledTr {...rowProps(row)}>
              {row.getVisibleCells().map((cell) => (
                <StyledTd
                  key={cell.id}
                  variant={cell.column.columnDef?.meta?.variant}
                  sticky={cell.column.columnDef?.meta?.sticky}
                  stickyOffset={cell.column.columnDef?.meta?.stickyOffset}
                >
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </StyledTd>
              ))}
            </StyledTr>
            {row.getIsExpanded() && renderSubComponent && (
              <StyledTr>
                <StyledTd colSpan={row.getVisibleCells().length}>
                  {renderSubComponent({ row })}
                </StyledTd>
              </StyledTr>
            )}
          </Fragment>
        ))}
      </tbody>
    );
  },
  (previous, next) =>
    previous.rows === next.rows &&
    previous.visibleColumns === next.visibleColumns &&
    hasSameTableState(previous.tableState, next.tableState) &&
    previous.rowProps === next.rowProps &&
    previous.renderSubComponent === next.renderSubComponent
);

const Table = ({
  table,
  config = {},
  renderSubComponent,
  rowProps = EMPTY_ROW_PROPS,
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
  const rows = table.getRowModel().rows;
  const tableState = table.getState();
  const visibleColumns = table.getVisibleLeafColumns();

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
          <MemoizedTableBody
            rows={rows}
            visibleColumns={visibleColumns}
            tableState={tableState}
            rowProps={rowProps}
            renderSubComponent={renderSubComponent}
          />
        </StyledTable>
        {isLoading && <LoadingOverlay />}
        {!isLoading && rows.length === 0 && <NoRowsOverlay />}
      </Box>
    </>
  );
};

export default Table;
