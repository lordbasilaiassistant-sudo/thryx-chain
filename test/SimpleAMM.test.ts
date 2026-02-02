import { expect } from "chai";
import { ethers } from "hardhat";
import { SimpleAMM, MockUSDC, MockWETH } from "../typechain-types";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("SimpleAMM", function () {
  let amm: SimpleAMM;
  let usdc: MockUSDC;
  let weth: MockWETH;
  let owner: SignerWithAddress;
  let user1: SignerWithAddress;
  let user2: SignerWithAddress;

  const INITIAL_USDC = ethers.parseUnits("10000", 6); // 10,000 USDC
  const INITIAL_WETH = ethers.parseEther("10"); // 10 WETH

  beforeEach(async function () {
    [owner, user1, user2] = await ethers.getSigners();

    // Deploy mock tokens
    const MockUSDC = await ethers.getContractFactory("MockUSDC");
    usdc = await MockUSDC.deploy();

    const MockWETH = await ethers.getContractFactory("MockWETH");
    weth = await MockWETH.deploy();

    // Deploy AMM
    const SimpleAMM = await ethers.getContractFactory("SimpleAMM");
    amm = await SimpleAMM.deploy(await usdc.getAddress(), await weth.getAddress());

    // Mint tokens to owner for liquidity
    await usdc.mint(owner.address, INITIAL_USDC);
    await weth.mint(owner.address, INITIAL_WETH);

    // Mint tokens to user for trading
    await usdc.mint(user1.address, ethers.parseUnits("1000", 6));
    await weth.mint(user1.address, ethers.parseEther("1"));
  });

  describe("Deployment", function () {
    it("Should set correct token addresses", async function () {
      expect(await amm.tokenA()).to.equal(await usdc.getAddress());
      expect(await amm.tokenB()).to.equal(await weth.getAddress());
    });

    it("Should start with zero reserves", async function () {
      expect(await amm.reserveA()).to.equal(0);
      expect(await amm.reserveB()).to.equal(0);
    });
  });

  describe("Add Liquidity", function () {
    it("Should allow adding liquidity", async function () {
      await usdc.approve(await amm.getAddress(), INITIAL_USDC);
      await weth.approve(await amm.getAddress(), INITIAL_WETH);
      
      await amm.addLiquidity(INITIAL_USDC, INITIAL_WETH);
      
      expect(await amm.reserveA()).to.equal(INITIAL_USDC);
      expect(await amm.reserveB()).to.equal(INITIAL_WETH);
    });

    it("Should mint LP tokens", async function () {
      await usdc.approve(await amm.getAddress(), INITIAL_USDC);
      await weth.approve(await amm.getAddress(), INITIAL_WETH);
      
      await amm.addLiquidity(INITIAL_USDC, INITIAL_WETH);
      
      const lpBalance = await amm.balanceOf(owner.address);
      expect(lpBalance).to.be.gt(0);
    });

    it("Should emit LiquidityAdded event", async function () {
      await usdc.approve(await amm.getAddress(), INITIAL_USDC);
      await weth.approve(await amm.getAddress(), INITIAL_WETH);
      
      await expect(amm.addLiquidity(INITIAL_USDC, INITIAL_WETH))
        .to.emit(amm, "LiquidityAdded");
    });
  });

  describe("Swap", function () {
    beforeEach(async function () {
      // Add liquidity first
      await usdc.approve(await amm.getAddress(), INITIAL_USDC);
      await weth.approve(await amm.getAddress(), INITIAL_WETH);
      await amm.addLiquidity(INITIAL_USDC, INITIAL_WETH);
    });

    it("Should swap USDC for WETH", async function () {
      const swapAmount = ethers.parseUnits("100", 6); // 100 USDC
      
      await usdc.connect(user1).approve(await amm.getAddress(), swapAmount);
      
      const wethBefore = await weth.balanceOf(user1.address);
      await amm.connect(user1).swap(await usdc.getAddress(), swapAmount, 0);
      const wethAfter = await weth.balanceOf(user1.address);
      
      expect(wethAfter).to.be.gt(wethBefore);
    });

    it("Should swap WETH for USDC", async function () {
      const swapAmount = ethers.parseEther("0.1"); // 0.1 WETH
      
      await weth.connect(user1).approve(await amm.getAddress(), swapAmount);
      
      const usdcBefore = await usdc.balanceOf(user1.address);
      await amm.connect(user1).swap(await weth.getAddress(), swapAmount, 0);
      const usdcAfter = await usdc.balanceOf(user1.address);
      
      expect(usdcAfter).to.be.gt(usdcBefore);
    });

    it("Should fail if output below minimum", async function () {
      const swapAmount = ethers.parseUnits("100", 6);
      const minOut = ethers.parseEther("100"); // Unrealistically high
      
      await usdc.connect(user1).approve(await amm.getAddress(), swapAmount);
      
      await expect(
        amm.connect(user1).swap(await usdc.getAddress(), swapAmount, minOut)
      ).to.be.revertedWith("Slippage exceeded");
    });

    it("Should emit Swap event", async function () {
      const swapAmount = ethers.parseUnits("100", 6);
      
      await usdc.connect(user1).approve(await amm.getAddress(), swapAmount);
      
      await expect(
        amm.connect(user1).swap(await usdc.getAddress(), swapAmount, 0)
      ).to.emit(amm, "Swap");
    });
  });

  describe("Price Functions", function () {
    beforeEach(async function () {
      await usdc.approve(await amm.getAddress(), INITIAL_USDC);
      await weth.approve(await amm.getAddress(), INITIAL_WETH);
      await amm.addLiquidity(INITIAL_USDC, INITIAL_WETH);
    });

    it("Should return current price", async function () {
      const price = await amm.getPrice();
      // Price = reserveA / reserveB = 10000e6 / 10e18
      expect(price).to.be.gt(0);
    });

    it("Should return expected output amount", async function () {
      const inputAmount = ethers.parseUnits("100", 6);
      const output = await amm.getAmountOut(await usdc.getAddress(), inputAmount);
      expect(output).to.be.gt(0);
    });
  });

  describe("Remove Liquidity", function () {
    beforeEach(async function () {
      await usdc.approve(await amm.getAddress(), INITIAL_USDC);
      await weth.approve(await amm.getAddress(), INITIAL_WETH);
      await amm.addLiquidity(INITIAL_USDC, INITIAL_WETH);
    });

    it("Should allow removing liquidity", async function () {
      const lpBalance = await amm.balanceOf(owner.address);
      const halfLp = lpBalance / 2n;
      
      const usdcBefore = await usdc.balanceOf(owner.address);
      const wethBefore = await weth.balanceOf(owner.address);
      
      await amm.removeLiquidity(halfLp);
      
      const usdcAfter = await usdc.balanceOf(owner.address);
      const wethAfter = await weth.balanceOf(owner.address);
      
      expect(usdcAfter).to.be.gt(usdcBefore);
      expect(wethAfter).to.be.gt(wethBefore);
    });
  });
});
