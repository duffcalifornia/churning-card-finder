import type { EngineData } from "../engine/types";
import cardsJson from "../../data/cards.json";
import currenciesJson from "../../data/currencies.json";
import programsJson from "../../data/programs.json";
import valuationsJson from "../../data/valuations.json";
import marriottMatrixJson from "../../data/marriott-matrix.json";

/** The data files the engine reads, bundled into the site. Nothing is fetched at run time. */
export const engineData = {
  catalog: cardsJson,
  currencies: currenciesJson,
  programs: programsJson,
  valuations: valuationsJson,
  marriottMatrix: marriottMatrixJson,
} as unknown as EngineData;
