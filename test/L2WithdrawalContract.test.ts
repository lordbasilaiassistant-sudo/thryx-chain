import { expect } from "chai";
import { ethers } from "hardhat";
import { SignerWithAddress } from "@nomicfoundation/hardhat-ethers/signers";

describe("L2WithdrawalContract", function () {
  let withdrawal: any;
  let mockToken: any;
  let owner: SignerWithAddress;
  let user1: SignerWithAddress;
  let user2: SignerWithAddress;

  beforeEach(async function () {
    [owner, user1, user2] = await ethers.getSigners();

    // Deploy mock token
    const MockToken = await ethers.getContractFactory("MockUSDC");
    mockToken = await MockToken.deploy();

    // Deploy L2WithdrawalContract (no constructor args)
    const L2Withdrawal = await ethers.getContractFactory("contracts/bridge/L2WithdrawalContract.sol:L2WithdrawalContract");
    withdrawal = await L2Withdrawal.deploy();

    // Set token mapping
    await withdrawal.setTokenMapping(await mockToken.getAddress(), user2.address); // dummy L1 address
  });

  describe("Deployment", function () {
    it("Should set correct owner", async function () {
      expect(await withdrawal.owner()).to.equal(owner.address);
    });

    it("Should start with zero withdrawals", async function () {
      expect(await withdrawal.withdrawalCount()).to.equal(0);
    });
  });

  describe("Token Mapping", function () {
    it("Should allow owner to set token mapping", async function () {
      const l2Token = await mockToken.getAddress();
      const l1Token = user1.address; // dummy
      await withdrawal.setTokenMapping(l2Token, l1Token);
      expect(await withdrawal.l2ToL1Token(l2Token)).to.equal(l1Token);
    });

    it("Should not allow non-owner to set mapping", async function () {
      await expect(
        withdrawal.connect(user1).setTokenMapping(await mockToken.getAddress(), user2.address)
      ).to.be.reverted;
    });
  });

  describe("Initiate Withdrawal", function () {
    beforeEach(async function () {
      // Mint tokens to user
      await mockToken.mint(user1.address, ethers.parseUnits("1000", 6));
      await mockToken.connect(user1).approve(await withdrawal.getAddress(), ethers.parseUnits("1000", 6));
    });

    it("Should allow user to initiate withdrawal", async function () {
      const amount = ethers.parseUnits("100", 6);
      await withdrawal.connect(user1).initiateWithdrawal(
        await mockToken.getAddress(),
        amount,
        user1.address
      );
      
      expect(await withdrawal.withdrawalCount()).to.equal(1);
    });

    it("Should emit WithdrawalInitiated event", async function () {
      const amount = ethers.parseUnits("100", 6);
      await expect(
        withdrawal.connect(user1).initiateWithdrawal(
          await mockToken.getAddress(),
          amount,
          user1.address
        )
      ).to.emit(withdrawal, "WithdrawalInitiated");
    });

    it("Should reject withdrawal for unmapped token", async function () {
      // Create a token that's not mapped
      const UnmappedToken = await ethers.getContractFactory("MockUSDC");
      const unmapped = await UnmappedToken.deploy();
      await unmapped.mint(user1.address, ethers.parseUnits("100", 6));
      await unmapped.connect(user1).approve(await withdrawal.getAddress(), ethers.parseUnits("100", 6));

      await expect(
        withdrawal.connect(user1).initiateWithdrawal(
          await unmapped.getAddress(),
          ethers.parseUnits("100", 6),
          user1.address
        )
      ).to.be.revertedWith("Token not bridgeable");
    });
  });

  describe("View Functions", function () {
    it("Should return user withdrawals", async function () {
      // Mint and approve
      await mockToken.mint(user1.address, ethers.parseUnits("1000", 6));
      await mockToken.connect(user1).approve(await withdrawal.getAddress(), ethers.parseUnits("1000", 6));

      // Create withdrawal
      await withdrawal.connect(user1).initiateWithdrawal(
        await mockToken.getAddress(),
        ethers.parseUnits("100", 6),
        user1.address
      );

      const userWithdrawals = await withdrawal.getUserWithdrawals(user1.address);
      expect(userWithdrawals.length).to.equal(1);
    });
  });
});
